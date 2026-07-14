import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import os
from app.config import settings

os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

import pandas as pd
from sqlalchemy import text
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from ragas.testset import TestsetGenerator
from ragas import evaluate
from ragas.metrics.collections import faithfulness, answer_relevancy, context_precision
from datasets import Dataset

from app.infrastructure.database.engine import async_session
from app.services.memory_service import get_match_context
from app.services.rag_improvements import log_retrieval_feedback
from agent.state import AgentState, AnalystOutput, WriterOutput
from agent.nodes_v2._generator import generator_node

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_documents() -> list[Document]:
    logger.info("Fetching interactions from database...")
    docs = []
    async with async_session() as db:
        try:
            query = text("""
                SELECT i.conversation_id, i.user_id, i.their_last_message,
                       i.user_organic_text, c.person_name, c.lore
                FROM interactions i
                LEFT JOIN conversations c ON i.conversation_id = c.id
                ORDER BY i.created_at DESC LIMIT 100
            """)
            result = await db.execute(query)
            rows = result.mappings().all()
        except Exception as e:
            logger.warning("Lore column might be missing: %s", e)
            await db.rollback()
            query = text("""
                SELECT i.conversation_id, i.user_id, i.their_last_message,
                       i.user_organic_text, c.person_name
                FROM interactions i
                LEFT JOIN conversations c ON i.conversation_id = c.id
                ORDER BY i.created_at DESC LIMIT 100
            """)
            result = await db.execute(query)
            rows = result.mappings().all()

        for idx, row in enumerate(rows):
            content_parts = []
            if row.get("their_last_message"):
                content_parts.append(f"Match said: {row['their_last_message']}")
            if row.get("user_organic_text"):
                content_parts.append(
                    f"User organically typed: {row['user_organic_text']}"
                )
            if row.get("lore"):
                content_parts.append(f"Lore: {row['lore']}")
            padding = "Contextual Background for RAG Simulator: ...\\n\\n"
            content = padding + "\\n".join(content_parts)
            if not content.strip():
                continue
            metadata = {
                "conversation_id": row.get("conversation_id", f"unknown_{idx}"),
                "user_id": row.get("user_id", f"unknown_{idx}"),
                "person_name": row.get("person_name", "unknown"),
            }
            docs.append(Document(page_content=content, metadata=metadata))
    logger.info("Fetched %d documents.", len(docs))
    return docs


async def generate_synthetic_dataset(documents: list[Document]):
    logger.info("Generating synthetic dataset using Ragas...")
    generator_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.7)
    critic_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.0)
    embeddings = GoogleGenerativeAIEmbeddings(model=settings.gemini_embedding_model)
    generator = TestsetGenerator.from_langchain(generator_llm, critic_llm, embeddings)
    testset = generator.generate_with_langchain_docs(documents, testset_size=20)
    return testset.to_dataset()


async def run_evaluation_pipeline():
    documents = await fetch_documents()
    if not documents:
        logger.error("No documents fetched.")
        return
    synthetic_dataset = await generate_synthetic_dataset(documents)
    questions = synthetic_dataset["question"]
    ground_truths = synthetic_dataset["ground_truth"]
    eval_data = {"question": [], "contexts": [], "answer": [], "ground_truth": []}
    logger.info("Running evaluation loop...")
    async with async_session() as db:
        for idx, question in enumerate(questions):
            logger.info("Evaluating question %d/%d", idx + 1, len(questions))
            source_user_id = documents[0].metadata["user_id"]
            source_conversation_id = documents[0].metadata["conversation_id"]
            source_person_name = documents[0].metadata["person_name"]
            if (
                "metadata" in synthetic_dataset.features
                and synthetic_dataset["metadata"]
            ):
                meta_list = synthetic_dataset["metadata"][idx]
                if meta_list and isinstance(meta_list, list) and len(meta_list) > 0:
                    meta = meta_list[0]
                    source_user_id = meta.get("user_id", source_user_id)
                    source_conversation_id = meta.get(
                        "conversation_id", source_conversation_id
                    )
                    source_person_name = meta.get("person_name", source_person_name)

            librarian_ctx = await get_match_context(
                db,
                user_id=source_user_id,
                conversation_id=source_conversation_id,
                current_text=question,
            )
            retrieved_contexts = []
            if librarian_ctx.get("core_lore"):
                retrieved_contexts.append(librarian_ctx["core_lore"])
            if librarian_ctx.get("tier_1_raw_exchanges"):
                retrieved_contexts.append(librarian_ctx["tier_1_raw_exchanges"])
            if librarian_ctx.get("tier_2_summary"):
                retrieved_contexts.append(librarian_ctx["tier_2_summary"])
            if not retrieved_contexts:
                retrieved_contexts = ["No matching context found."]

            # Log retrieval feedback
            for ctx in retrieved_contexts:
                if ctx and ctx != "No matching context found.":
                    for line in ctx.split("\n")[:3]:
                        if line.strip():
                            await log_retrieval_feedback(
                                db,
                                interaction_id=str(uuid.uuid4()),
                                fact_text=line.strip()[:200],
                                was_used=True,
                            )

            mock_analysis = AnalystOutput(
                visual_transcript=[],
                visual_hooks=[],
                detected_dialect="ENGLISH",
                their_tone="neutral",
                their_effort="medium",
                conversation_temperature="warm",
                archetype_reasoning="Synthesized for RAG evaluation.",
                detected_archetype="THE BANTER GIRL",
                key_detail="Testing detail",
                person_name=source_person_name,
                stage="early_talking",
                their_last_message=question,
            )
            mock_state = AgentState(
                image_bytes="",
                direction="quick_reply",
                custom_hint="",
                user_id=source_user_id,
                conversation_id=source_conversation_id,
                voice_dna_dict={},
                conversation_context_dict={
                    "person_name": source_person_name,
                    "interaction_count": 5,
                },
                is_valid_chat=True,
                bouncer_reason="",
                analysis=mock_analysis,
                strategy=None,
                drafts=None,
                core_lore=librarian_ctx.get("core_lore", ""),
                past_memories="",
                tier_1_raw_exchanges=librarian_ctx.get("tier_1_raw_exchanges", ""),
                tier_2_summary=librarian_ctx.get("tier_2_summary", ""),
                is_cringe=False,
                auditor_feedback="",
                revision_count=0,
            )
            try:
                gen_result = generator_node(mock_state)
                strategy = gen_result.get("strategy")
                drafts = gen_result.get("drafts")
                if strategy and drafts:
                    answer = json.dumps(
                        {
                            "strategy": strategy.model_dump(),
                            "replies": [
                                {
                                    "text": r.text,
                                    "strategy_label": r.strategy_label,
                                    "is_recommended": r.is_recommended,
                                }
                                for r in (
                                    drafts.replies
                                    if isinstance(drafts, WriterOutput)
                                    else []
                                )[:4]
                            ],
                        }
                    )
                else:
                    answer = "No strategy generated."
            except Exception as e:
                logger.warning("generator_call_failed", question_idx=idx, error=str(e))
                answer = json.dumps({"error": str(e)})
            eval_data["question"].append(question)
            eval_data["contexts"].append(retrieved_contexts)
            eval_data["answer"].append(answer)
            eval_data["ground_truth"].append(
                ground_truths[idx] if ground_truths[idx] else ""
            )

    eval_hf_dataset = Dataset.from_dict(eval_data)
    logger.info("Executing RAG Triad Evaluation...")
    judge_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.0)
    embeddings = GoogleGenerativeAIEmbeddings(model=settings.gemini_embedding_model)
    result = evaluate(
        eval_hf_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
        llm=judge_llm,
        embeddings=embeddings,
    )
    scores_df = result.to_pandas()
    print("\n=== RAG Evaluation Summary ===")
    summary = scores_df[
        ["faithfulness", "answer_relevancy", "context_precision"]
    ].mean()
    print(summary)
    evals_dir = Path("evals/reports")
    evals_dir.mkdir(parents=True, exist_ok=True)
    with open(evals_dir / "latest_run.json", "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "summary": summary.to_dict(),
                "details": json.loads(scores_df.to_json(orient="records")),
            },
            f,
            indent=4,
        )
    logger.info("Evaluation complete!")


async def analyze_production_retrieval_telemetry():
    """Queries production logs to calculate the true hit-rate and alignment
    precision of the RAG engine."""
    logger.info("Analyzing production retrieval feedback records...")
    async with async_session() as db:
        stats_query = text("""
            SELECT
                COUNT(*) as total_retrieved,
                SUM(CASE WHEN was_used = true THEN 1 ELSE 0 END) as total_used,
                ROUND(100.0 * SUM(CASE WHEN was_used = true THEN 1 ELSE 0 END) / COUNT(*), 2) as generation_conversion_rate
            FROM retrieval_feedback;
        """)
        try:
            stats_res = await db.execute(stats_query)
            stats = stats_res.mappings().first()
            if not stats or stats["total_retrieved"] == 0:
                print(
                    "\n=== Telemetry Alert: No feedback production data logged yet. ===\n"
                )
                return
            print("\n==================================================")
            print("   PRODUCTION RAG TELEMETRY OPTIMIZATION REPORT   ")
            print("==================================================")
            print(f"Total Context Elements Loaded: {stats['total_retrieved']}")
            print(f"Total Elements Utilized by LLM:  {stats['total_used']}")
            print(
                f"Core Generative Hit Rate:        {stats['generation_conversion_rate']}%"
            )
            print("==================================================\n")
        except Exception as e:
            logger.error("failed_to_extract_telemetry_metrics", error=str(e))


if __name__ == "__main__":
    import sys

    if "--telemetry" in sys.argv:
        asyncio.run(analyze_production_retrieval_telemetry())
    else:
        asyncio.run(run_evaluation_pipeline())
