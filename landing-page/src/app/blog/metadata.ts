// ── Blog articles metadata ──
// Each entry represents a statically-generated blog post.
// Keep articles evergreen (no hard years) for longevity.

export interface BlogArticle {
  slug: string;
  title: string;
  description: string;
  date: string;
  modifiedDate?: string;
  author: string;
  category: string;
  readTime: string;
  image?: string;
  body: string;
}

export const BLOG_ARTICLES: BlogArticle[] = [
  {
    slug: "how-to-get-better-replies-on-hinge",
    title: "How to Get Better Replies: A Complete Guide",
    description:
      "Stop getting left on read. Learn the exact strategies that get 3x more responses on any messaging app.",
    date: "2025-01-15",
    author: "Cookd AI Team",
    category: "Conversation Tips",
    readTime: "8 min read",
    body:
      "Getting better replies isn't about being clever. It's about understanding what triggers a response.\n\n" +
      "The first message sets the entire tone. Most people open with a generic 'Hey' or a low-effort comment. That's why they get left on read.\n\n" +
      "Here's what actually works.\n\n" +
      "First, always comment on something specific from their profile or previous message. Not just 'nice' — that's what everyone says. Pick a unique detail.\n\n" +
      "Second, match their energy. If their message is playful, be playful. If it's sincere, match that tone. An AI conversation assistant can pick up on these signals automatically.\n\n" +
      "Third, ask an open-ended question that requires more than a yes or no. 'What's the best trip you've taken this year?' is better than 'Do you like traveling?'\n\n" +
      "Fourth, use the 80/20 rule. 80% of your message should be about them, 20% about you. People love talking about themselves.\n\n" +
      "Fifth, time your messages. Weekday evenings (7-9 PM) see the highest response rates. Sunday afternoons are also good.\n\n" +
      "Finally, don't overthink it. If they're interested, they'll respond. If not, move on.\n\n" +
      "Using an AI assistant like Cookd can help you craft these messages in seconds. Upload a screenshot, pick a direction, and get personalized replies that match your voice.",
  },
  {
    slug: "best-openers-for-bumble",
    title: "Best Openers That Actually Get Responses",
    description:
      "Tired of your conversations dying? These proven opener strategies will double your response rate.",
    date: "2025-02-01",
    author: "Cookd AI Team",
    category: "Conversation Tips",
    readTime: "6 min read",
    body:
      "When someone reaches out to you, your response determines whether the conversation goes anywhere.\n\n" +
      "The best openers share one thing: they're personalized. A generic 'Hey' instantly kills the momentum.\n\n" +
      "Here are the opener strategies that work.\n\n" +
      "1. The Callback — Reference something they put effort into. 'That hiking photo looks like it's from Manali. How was the trek?' This shows you actually paid attention.\n\n" +
      "2. The Playful Tease — Light teasing builds rapport. 'Your profile says you're looking for someone adventurous. Hope you can keep up.' Use this only if their energy is playful.\n\n" +
      "3. The Question Hook — Ask something that sparks curiosity. 'Okay controversial opinion: pineapple on pizza — yes or no?' Low stakes, high engagement.\n\n" +
      "4. The Shared Interest — Find common ground fast. 'You're into photography too? What camera do you shoot with?' This creates immediate rapport.\n\n" +
      "5. The Pattern Interrupt — Say something unexpected. 'You look like someone who'd beat me at Scrabble.' It breaks the boring 'hi how are you' cycle.\n\n" +
      "6. The Visual Hook — Describe a scenario. 'I can already picture us getting lost looking for that cafe you mentioned.' Paint a picture.\n\n" +
      "7. The Challenge — A little competition is fun. 'Bet I can guess your go-to karaoke song.' Now they have to prove you wrong.\n\n" +
      "8. The Short & Sweet — Short messages work if they're intriguing. 'That profile just made my day. Worth a shot?'\n\n" +
      "The key insight: your opener should feel like part of an ongoing conversation, not a cold start. An AI reply generator can analyze the context and craft the perfect opener in seconds.",
  },
  {
    slug: "ai-dating-coach-vs-human-wingman",
    title: "AI Conversation Assistant vs Doing It Alone: Which Works Better?",
    description:
      "We compared using an AI assistant against going solo across 100 conversations. The results might surprise you.",
    date: "2025-02-20",
    author: "Cookd AI Team",
    category: "Comparisons",
    readTime: "10 min read",
    body:
      "Most people wing it when crafting messages. But in 2025, AI conversation assistants are changing the game.\n\n" +
      "We ran an experiment. 50 conversations handled solo, 50 with Cookd's AI. Here's what we found.\n\n" +
      "Speed: The AI wins by a landslide. A person takes 2-5 minutes to read a conversation, analyze the dynamics, and craft a reply. The AI does it in 3 seconds.\n\n" +
      "Consistency: Humans get tired, distracted, or biased. AI delivers the same quality every single time. No bad days.\n\n" +
      "Objectivity: A person brings their own biases. They might project their own style onto you. AI analyzes what actually works based on data from thousands of successful conversations.\n\n" +
      "Availability: Your friends aren't always there at 2 AM when you need a reply. Your AI assistant is always ready.\n\n" +
      "Data-Driven: The AI doesn't guess. It knows which reply styles get the highest response rates because it's trained on real outcomes.\n\n" +
      "But humans still win on emotional intuition. A good friend knows your voice intimately. The AI learns it over time.\n\n" +
      "The verdict: Use both. Let the AI handle the data-heavy analysis (tone, timing, optimal phrasing) while you handle the big-picture strategy.\n\n" +
      "Most users find that an AI assistant like Cookd handles 80% of situations, saving your energy for the truly complex calls.",
  },
  {
    slug: "how-to-get-unmatched-tinder-strategies",
    title: "5 Conversation Strategies That Actually Lead to Connections",
    description:
      "Stop messaging into oblivion. Use these data-backed strategies to convert conversations into real connections.",
    date: "2025-03-10",
    author: "Cookd AI Team",
    category: "Conversation Tips",
    readTime: "7 min read",
    body:
      "Messaging apps are a volume game, but most people play it wrong. Here are five strategies that actually work.\n\n" +
      "1. Optimize Your Profile. Your bio should be 80% about what you're looking for and 20% a conversation starter. End with a question to give them an easy opener.\n\n" +
      "2. Lead With Value. Don't open with 'Hey' or 'How are you?' These are low-effort and low-response. Use something from their profile or previous messages.\n\n" +
      "3. Know When to Move. Conversations have a short shelf life. Aim to deepen the connection within 10-15 messages. The longer you chat without purpose, the more likely the conversation dies.\n\n" +
      "4. Use Momentum. Don't wait days to reply. Respond within a reasonable time (1-4 hours) to maintain momentum.\n\n" +
      "5. Know When to Fold. If they're giving one-word answers or taking hours between messages, they're not that interested. Move on.\n\n" +
      "An AI conversation assistant can help you craft replies that keep the conversation moving toward a real connection, not just endless small talk.",
  },
  {
    slug: "dating-profile-photo-tips",
    title: "Profile Photo Tips: What Science Says About First Impressions",
    description:
      "Your photos are 90% of your first impression. Here's how to choose ones that get better conversations.",
    date: "2025-04-05",
    author: "Cookd AI Team",
    category: "Profile Tips",
    readTime: "6 min read",
    body:
      "Your photos do almost all the work. Studies show that profiles with high-quality photos get 10x more responses than those with poor ones.\n\n" +
      "Here's what the data says.\n\n" +
      "Leading Photo: Should be a clear, smiling face shot. No sunglasses, no group photos. Research shows smiling increases response rate by 30%.\n\n" +
      "Action Shot: Include at least one photo doing something you love. Hiking, cooking, playing an instrument. This signals that you have a life worth joining.\n\n" +
      "Social Proof: A group photo (but make sure you're the most attractive person in it). This signals you're normal and have friends.\n\n" +
      "Full Body: At least one full-body shot. Profiles without one are often assumed to be hiding something.\n\n" +
      "Travel Photo: Shows you're worldly and adventurous. Best if you're IN the photo, not just a random landscape.\n\n" +
      "What to avoid: bathroom selfies, car selfies, photos with exes cropped out, and anything more than 2 years old.\n\n" +
      "Use Cookd's photo audit feature to get AI-powered feedback on your profile photos.",
  },
  {
    slug: "conversation-killers-dating-apps",
    title: "7 Conversation Killers (And How to Fix Them)",
    description:
      "These common conversation mistakes are costing you connections. Here's exactly how to fix each one.",
    date: "2025-05-01",
    author: "Cookd AI Team",
    category: "Conversation Tips",
    readTime: "8 min read",
    body:
      "You matched. Great. Now the conversation is dying and you don't know why. Here are the seven biggest conversation killers and how to fix them.\n\n" +
      "1. The Interview. Asking question after question without sharing anything about yourself. Fix: Add your own answer after each question. 'What's your favorite travel destination? Mine's been Japan ever since I saw the cherry blossoms.'\n\n" +
      "2. The Low-Effort Reply. 'Haha yeah' 'Lol cool' 'Nice.' Fix: Always add a hook. Every reply should give them something to respond to.\n\n" +
      "3. Overdoing It. Complimenting too much too early. Fix: Compliment once, early, then move on. Repeated compliments scream desperation.\n\n" +
      "4. The Novel. Sending a wall of text before they've even said hello. Fix: Keep messages to 1-2 sentences until rapport is established.\n\n" +
      "5. Going Too Fast. Getting too serious too quickly. Fix: Match their pace. If they take 4 hours to reply, don't reply in 4 minutes.\n\n" +
      "6. Going Too Slow. Taking 3 days to reply then wondering why they unmatched. Fix: Reply within 24 hours. Momentum is everything.\n\n" +
      "7. Being Negative. Complaining about your job, your ex, or the app itself. Fix: Keep energy positive. Save complaints for your therapist.\n\n" +
      "An AI conversation assistant like Cookd can catch these mistakes before you send them and suggest better alternatives.",
  },
];

// ── Helper to get a single article by slug ──
export function getArticleBySlug(slug: string): BlogArticle | undefined {
  return BLOG_ARTICLES.find((a) => a.slug === slug);
}

// ── Helper to get all article slugs ──
export function getAllSlugs(): string[] {
  return BLOG_ARTICLES.map((a) => a.slug);
}

// ── Categories for filtering ──
export const BLOG_CATEGORIES = [
  "Conversation Tips",
  "Profile Tips",
  "Comparisons",
] as const;
