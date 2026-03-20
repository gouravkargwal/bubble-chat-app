import asyncio
import json
import logging
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
from agent.nodes import strategist_node
from agent.state import AgentState, AnalystOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_documents() -> list[Document]:
    logger.info("Fetching interactions from database...")
    docs = []
    async with async_session() as db:
        # Fetch last 100 rows, left joining conversations
        # We handle 'lore' cautiously via text() execution checking if column exists is hard,
        # but try/except block around different select queries is safest.
        try:
            query = text("""
                SELECT 
                    i.conversation_id, 
                    i.user_id, 
                    i.their_last_message, 
                    i.user_organic_text, 
                    c.person_name, 
                    c.lore 
                FROM interactions i
                LEFT JOIN conversations c ON i.conversation_id = c.id
                ORDER BY i.created_at DESC 
                LIMIT 100
            """)
            result = await db.execute(query)
            rows = result.mappings().all()
        except Exception as e:
            logger.warning("Lore column might be missing. Proceeding without lore: %s", e)
            await db.rollback()
            query = text("""
                SELECT 
                    i.conversation_id, 
                    i.user_id, 
                    i.their_last_message, 
                    i.user_organic_text, 
                    c.person_name 
                FROM interactions i
                LEFT JOIN conversations c ON i.conversation_id = c.id
                ORDER BY i.created_at DESC 
                LIMIT 100
            """)
            result = await db.execute(query)
            rows = result.mappings().all()

        for idx, row in enumerate(rows):
            content_parts = []
            if row.get("their_last_message"):
                content_parts.append(f"Match said: {row['their_last_message']}")
            if row.get("user_organic_text"):
                content_parts.append(f"User organically typed: {row['user_organic_text']}")
            if row.get("lore"):
                content_parts.append(f"Lore: {row['lore']}")
            
            padding = (
                "Contextual Background for RAG Simulator: This is an interaction snapshot from a dating text-coach application. "
                "The underlying mechanics function by analyzing the conversation's tone, effort, temperature, and dialect to propose "
                "strategic text-message replies that employ tactics like 'PATTERN INTERRUPT' or 'SOFT CLOSE'. The following snippets "
                "represent a localized moment in the user's ongoing conversation with their match. We will use this content to synthesize "
                "realistic interaction queries for our AI agent and determine the faithfulness and relevancy of its generated strategies.\\n\\n"
            )
            content = padding + "\\n".join(content_parts)
            if not content.strip():
                continue

            metadata = {
                "conversation_id": row.get("conversation_id", f"unknown_{idx}"),
                "user_id": row.get("user_id", f"unknown_{idx}"),
                "person_name": row.get("person_name", "unknown")
            }
            docs.append(Document(page_content=content, metadata=metadata))
    
    logger.info("Fetched %d documents.", len(docs))
    return docs

async def generate_synthetic_dataset(documents: list[Document]):
    logger.info("Generating synthetic dataset using Ragas...")
    
    generator_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.7)
    critic_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    generator = TestsetGenerator.from_langchain(
        generator_llm,
        critic_llm,
        embeddings
    )

    testset = generator.generate_with_langchain_docs(
        documents,
        testset_size=20
    )
    return testset.to_dataset()

async def run_evaluation_pipeline():
    # 1. Ingestion
    documents = await fetch_documents()
    if not documents:
        logger.error("No documents fetched. Ensure database has interaction data.")
        return

    # 2. Synthetic Dataset Generation
    synthetic_dataset = await generate_synthetic_dataset(documents)
    
    questions = synthetic_dataset["question"]
    ground_truths = synthetic_dataset["ground_truth"]
    
    eval_data = {
        "question": [],
        "contexts": [],
        "answer": [],
        "ground_truth": []
    }

    logger.info("Running evaluation loop...")
    
    # 3. Test Runner
    async with async_session() as db:
        for idx, question in enumerate(questions):
            logger.info("Evaluating question %d/%d", idx + 1, len(questions))
            
            # Since testset generation mixes document contexts, we blindly take the first doc's 
            # metadata we can find in the context or just use a generic ID for librarian.
            # Ragas testset attaches source metadata if configured.
            # We'll default to the first available if not found.
            
            source_user_id = documents[0].metadata["user_id"]
            source_conversation_id = documents[0].metadata["conversation_id"]
            source_person_name = documents[0].metadata["person_name"]
            
            if "metadata" in synthetic_dataset.features and synthetic_dataset["metadata"]:
                meta_list = synthetic_dataset["metadata"][idx]
                if meta_list and isinstance(meta_list, list) and len(meta_list) > 0:
                    meta = meta_list[0]
                    source_user_id = meta.get("user_id", source_user_id)
                    source_conversation_id = meta.get("conversation_id", source_conversation_id)
                    source_person_name = meta.get("person_name", source_person_name)

            # Call Librarian
            librarian_ctx = await get_match_context(
                db,
                user_id=source_user_id,
                conversation_id=source_conversation_id,
                current_text=question
            )
            
            # Form context list
            retrieved_contexts = []
            if librarian_ctx["core_lore"]:
                retrieved_contexts.append(librarian_ctx["core_lore"])
            if librarian_ctx["past_memories"]:
                retrieved_contexts.append(librarian_ctx["past_memories"])
                
            if not retrieved_contexts:
                retrieved_contexts = ["No matching context found."]

            # Mock AnalystOutput for Chef
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
                their_last_message=question
            )
            
            mock_state = AgentState(
                image_bytes="",
                direction="default",
                custom_hint="",
                user_id=source_user_id,
                conversation_id=source_conversation_id,
                voice_dna_dict={},
                conversation_context_dict={},
                is_valid_chat=True,
                bouncer_reason="",
                analysis=mock_analysis,
                strategy=None,
                drafts=None,
                core_lore=librarian_ctx["core_lore"],
                past_memories=librarian_ctx["past_memories"],
                is_cringe=False,
                auditor_feedback="",
                revision_count=0
            )

            # Call Chef
            result_state = strategist_node(mock_state)
            strategy = result_state["strategy"]
            if strategy:
                answer = strategy.model_dump_json()
            else:
                answer = "No strategy generated."

            eval_data["question"].append(question)
            eval_data["contexts"].append(retrieved_contexts)
            eval_data["answer"].append(answer)
            eval_data["ground_truth"].append(ground_truths[idx] if ground_truths[idx] else "")

    eval_hf_dataset = Dataset.from_dict(eval_data)
    
    # 4. RAG Triad Scoring
    logger.info("Executing RAG Triad Evaluation...")
    judge_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    result = evaluate(
        eval_hf_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
        llm=judge_llm,
        embeddings=embeddings
    )
    
    scores_df = result.to_pandas()
    
    # 5. Reporting
    print("\\n=== RAG Evaluation Summary ===")
    summary = scores_df[['faithfulness', 'answer_relevancy', 'context_precision']].mean()
    print(summary)
    print("==============================\\n")
    
    # Export JSON
    evals_dir = Path("evals/reports")
    evals_dir.mkdir(parents=True, exist_ok=True)
    report_path = evals_dir / "latest_run.json"
    
    report_dict = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary.to_dict(),
        "details": json.loads(scores_df.to_json(orient="records"))
    }
    
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=4)
        
    logger.info("Evaluation complete! Report saved to %s", report_path)

if __name__ == "__main__":
    asyncio.run(run_evaluation_pipeline())
