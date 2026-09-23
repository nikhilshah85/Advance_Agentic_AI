"""
multi_agent_demo.py
====================

A minimal, fully self-contained multi-agent workflow demo.
No API key required, no internet required — it just runs.

Agents:
    Planner     -> breaks the user's request into subtasks
    Researcher  -> gathers "facts" for the topic
    Writer      -> drafts content based on the research
    Reviewer    -> critiques the draft; approves or sends it back for a
                   revision (capped so the agents don't bicker forever,
                   unlike some group chats we could mention)

An Orchestrator wires the agents together with simple message passing,
including a Writer <-> Reviewer feedback loop.

Usage:
    python multi_agent_demo.py
    python multi_agent_demo.py "artificial intelligence in healthcare"
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os
import sys


# ---------------------------------------------------------------------------
# 1. Message — the only thing agents are allowed to pass between each other
# ---------------------------------------------------------------------------
@dataclass
class Message:
    sender: str
    receiver: str
    content: str
    msg_type: str = "info"  # "plan" | "research" | "draft" | "feedback" | "approval"
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        preview = self.content.strip().replace("\n", " ")[:70]
        return f"[{self.sender:>10} -> {self.receiver:<12}] ({self.msg_type}): {preview}"


# ---------------------------------------------------------------------------
# 2. Base Agent
# ---------------------------------------------------------------------------
class Agent:
    """Every agent gets a name and (optionally) a real LLM to call."""

    def __init__(self, name: str):
        self.name = name

    def act(self, message: Message) -> Message:
        raise NotImplementedError

    def call_llm(self, prompt: str) -> str:
        """
        Swap-in point for a real model.

        If ANTHROPIC_API_KEY is set in the environment, this calls Claude
        for real. Otherwise it falls back to a deterministic offline stub,
        so the demo always runs — no key, no network, no excuses.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        print(api_key);
        if api_key:
            try:
                import anthropic  # pip install anthropic

                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception as exc:  # network issues, bad key, etc.
                return f"[LLM call failed ({exc}), using offline stub instead]\n" + self._stub(prompt)
        return self._stub(prompt)

    def _stub(self, prompt: str) -> str:
        return f"[offline stub response for: {prompt[:60]}...]"


# ---------------------------------------------------------------------------
# 3. Concrete Agents
# ---------------------------------------------------------------------------
class PlannerAgent(Agent):
    """Breaks the request into a short subtask list."""

    def act(self, message: Message) -> Message:
        topic = message.content
        subtasks = [
            f"Research key facts about: {topic}",
            f"Write a short draft about: {topic}",
            "Review the draft for accuracy and tone",
        ]
        plan_text = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(subtasks))
        return Message(self.name, "orchestrator", plan_text, msg_type="plan",
                        metadata={"subtasks": subtasks})


class ResearcherAgent(Agent):
    """Gathers 'facts'. Swap this for a real search/RAG call any time."""

    FACT_BANK = {
        "renewable energy": [
            "Solar panel costs have dropped more than 80% over the last decade.",
            "Wind power is now among the cheapest sources of new electricity in many regions.",
            "Grid-scale battery storage is the main bottleneck for wider adoption.",
        ],
        "default": [
            "This topic has grown in relevance over the last few years.",
            "Most experts agree it involves real trade-offs worth weighing.",
            "Public interest in this area has increased steadily.",
        ],
    }

    def act(self, message: Message) -> Message:
        topic_lower = message.content.lower()
        facts = next((v for k, v in self.FACT_BANK.items() if k in topic_lower),
                     self.FACT_BANK["default"])
        content = "\n".join(f"- {f}" for f in facts)
        return Message(self.name, "orchestrator", content, msg_type="research")


class WriterAgent(Agent):
    """Drafts a short piece, incorporating reviewer feedback if any."""

    def act(self, message: Message) -> Message:
        topic = message.metadata.get("topic", "the topic")
        research = message.metadata.get("research", "")
        feedback = message.metadata.get("feedback")

        draft = (
            f"{topic.title()}: A Quick Look\n\n"
            f"{research}\n\n"
            f"In short, {topic} remains worth watching closely as these "
            f"trends continue to develop."
        )

        if feedback:
            draft += f"\n\n(Revised per feedback: {feedback})"

        return Message(self.name, "orchestrator", draft, msg_type="draft")


class ReviewerAgent(Agent):
    """
    A deliberately opinionated critic: it always asks for one revision on
    the first pass, purely so this demo actually shows you the feedback
    loop instead of rubber-stamping everything like a tired manager on
    a Friday afternoon.
    """

    def act(self, message: Message) -> Message:
        revision_round = message.metadata.get("revision_round", 0)

        if revision_round == 0:
            feedback = "Add a stronger closing sentence about future outlook."
            return Message(self.name, "orchestrator", feedback, msg_type="feedback")

        return Message(self.name, "orchestrator", "Approved.", msg_type="approval")


# ---------------------------------------------------------------------------
# 4. Orchestrator — wires the agents together and runs the workflow
# ---------------------------------------------------------------------------
class Orchestrator:
    MAX_REVISIONS = 2  # hard stop, in case the Reviewer never stops nitpicking

    def __init__(self):
        self.planner = PlannerAgent("Planner")
        self.researcher = ResearcherAgent("Researcher")
        self.writer = WriterAgent("Writer")
        self.reviewer = ReviewerAgent("Reviewer")
        self.log: List[Message] = []

    def _record(self, msg: Message) -> None:
        self.log.append(msg)
        print(msg)

    def run(self, topic: str) -> str:
        print(f"\n=== Starting multi-agent workflow for: '{topic}' ===\n")

        # Step 1: Plan
        plan_msg = self.planner.act(Message("orchestrator", "Planner", topic))
        self._record(plan_msg)

        # Step 2: Research
        research_msg = self.researcher.act(Message("orchestrator", "Researcher", topic))
        self._record(research_msg)

        # Step 3: Write, with a Writer <-> Reviewer revision loop
        feedback: Optional[str] = None
        draft = ""

        for round_num in range(self.MAX_REVISIONS + 1):
            write_input = Message(
                "orchestrator", "Writer", topic,
                metadata={"topic": topic, "research": research_msg.content, "feedback": feedback},
            )
            draft_msg = self.writer.act(write_input)
            self._record(draft_msg)
            draft = draft_msg.content

            review_input = Message(
                "orchestrator", "Reviewer", draft,
                metadata={"revision_round": round_num},
            )
            review_msg = self.reviewer.act(review_input)
            self._record(review_msg)

            if review_msg.msg_type == "approval":
                break
            feedback = review_msg.content

        print("\n=== Final Output ===\n")
        print(draft)
        return draft


# ---------------------------------------------------------------------------
# 5. Run it
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    topic_arg = " ".join(sys.argv[1:]) or "renewable energy"
    print("Deploying a small team of very confident digital interns...")
    Orchestrator().run(topic_arg)
