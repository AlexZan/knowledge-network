# Scenario: Starting a New Chat with Prior Context

## The Session

I open my terminal and type `oi chat`. The system starts up and presents me with a prompt.

I type: "I want to work on the payment integration."

The AI responds:

```
I found related context:

RELATED CHATS:
  1. "Payment Gateway Research" (3 days ago)
     Summary: Compared Stripe vs PayPal, decided on Stripe
     Artifacts: 4 (2 facts, 1 resolved effort, 1 open effort)

  2. "API Design Session" (last week)
     Summary: Designed REST endpoints for checkout flow
     Artifacts: 6 (3 facts, 3 resolved efforts)

RELEVANT ARTIFACTS:
  • [fact] Using Stripe API v2023-10
  • [fact] Webhook endpoint: /api/webhooks/stripe
  • [effort:open] Implement refund logic

Options:
  1. Continue "Payment Gateway Research" (has open effort)
  2. Fork from "API Design Session"
  3. New chat with selected artifacts
  4. Start fresh (no prior context)
```

I think about it. I want to pick up where I left off with the refund logic, but I also want the API design context. I type: `3, include 1,2`.

The AI confirms: "Starting new chat with artifacts: Stripe API v2023-10, webhook endpoint, and refund logic. Loading context..."

I see the chat interface appear. The AI's first message includes: "I see you want to work on payment integration. You previously decided on Stripe API v2023-10, have a webhook endpoint at /api/webhooks/stripe, and have an open effort to implement refund logic. Where would you like to start?"

I reply: "Let's tackle the refund logic first. I need to understand what data we need to store."

We have a back-and-forth discussion about refund requirements. The AI asks clarifying questions, I provide details about our business rules. After about 10 messages, we've outlined the refund flow.

I type: "Okay, I think we have it. We need to store: refund reason, amount, original transaction ID, and timestamp. The status can be pending, processed, or failed."

The AI responds: "Great! Let me capture that as an artifact."

I see a brief indicator that says "Artifact created: Refund data model."

The conversation continues. We discuss implementation details for another 15 messages. At one point, I get confused about the webhook signature verification.

I ask: "Wait, how do we verify Stripe webhooks again?"

The AI immediately responds: "From our previous context: webhook endpoint is /api/webhooks/stripe. You're using Stripe API v2023-10. The signature verification uses the webhook secret from your Stripe dashboard with the raw request body."

I realize I never mentioned the endpoint or API version in this chat - the AI remembered from the artifacts we imported at the start.

We work through the signature verification code. After several attempts and debugging messages, I finally get it working.

I type: "Perfect! The webhook verification is working now. Let's move on to the actual refund processing."

The AI responds: "I'll capture the webhook verification solution as a resolved effort."

Another artifact indicator appears.

We continue working for another 20 messages, implementing the refund processor. Finally, I type: "I think that covers it. The refund logic is implemented and tested."

The AI says: "Excellent! Let me create the final artifact for the refund implementation effort."

I see: "Artifact created: Refund processor implementation (resolved)."

The AI adds: "You now have 3 new artifacts from this session. Your context for future payment work will include: refund data model, webhook verification solution, and refund processor implementation."

I type `:quit` to end the session.

## What I Observed

- When I started a new chat about payment integration, the system found my previous related chats and artifacts
- I could choose how to continue: pick an existing chat, fork, start new with selected artifacts, or start fresh
- The AI remembered facts from imported artifacts without me repeating them
- During our conversation, the system automatically created artifacts when we reached conclusions
- Each artifact capture happened naturally at resolution points, not interrupting the flow
- The context stayed focused on our current discussion, not bloated with all past conversation history
- At the end, I had portable knowledge (artifacts) that could be used in future sessions

## What I Didn't Have To Do

- Manually search through old chat logs to find relevant information
- Copy-paste code or decisions from previous sessions
- Remember all the details about Stripe API version or webhook endpoint
- Explicitly tell the system to "save this information for later"
- Worry about hitting a token limit despite having a long, productive session
- Re-explain context that was established in previous conversations
- Manually organize or tag the knowledge we created