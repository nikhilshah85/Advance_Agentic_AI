"""
multi_agent_demo.py
====================

A minimal multi-agent workflow demo that runs two ways:

  - OFFLINE (default): no API key needed, deterministic canned logic,
    so the architecture always works end to end even with zero setup.
  - LIVE: set ANTHROPIC_API_KEY and `pip install anthropic`, and every
    agent will actually call Claude instead of the canned logic.

Agents:
    Planner     -> breaks the user's request into subtasks
    Researcher  -> gathers facts for the topic
    Writer      -> drafts content based on the research
    Reviewer    -> approves the draft or sends it back with feedback
                   (capped revisions, so the agents don't bicker forever)

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
# 1. Message - the only thing agents are allowed to pass between each other
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
    """Every agent gets a name and can optionally call a real LLM."""

    def __init__(self, name: str):
        self.name = name
        self.has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
      
    def act(self, message: Message) -> Message:
        raise NotImplementedError

    def _call_claude(self, prompt: str) -> str:
        """Calls the real Anthropic API. Raises on any failure - the
        caller decides what to do about it (usually: fall back)."""
        import anthropic  # pip install anthropic

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY itself
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _try_llm(self, prompt: str) -> Optional[str]:
        """Returns Claude's response, or None if unavailable/failed -
        in which case the agent quietly falls back to canned logic
        instead of grinding the whole demo to a halt."""
        if not self.has_api_key:
            return None
        try:
            return self._call_claude(prompt)
        except Exception as exc:
            print(f"    [!] {self.name}: live call failed ({exc}) - using offline logic instead")
            return None


# ---------------------------------------------------------------------------
# 3. Concrete Agents
# ---------------------------------------------------------------------------
class PlannerAgent(Agent):
    def act(self, message: Message) -> Message:
        topic = message.content
        prompt = (
            f"Break this task into exactly 3 short numbered subtasks, "
            f"one per line, no extra commentary. Task: {topic}"
        )
        plan_text = self._try_llm(prompt)
        if plan_text is None:
            subtasks = [
                f"Research key facts about: {topic}",
                f"Write a short draft about: {topic}",
                "Review the draft for accuracy and tone",
            ]
            plan_text = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(subtasks))
        return Message(self.name, "orchestrator", plan_text, msg_type="plan")


class ResearcherAgent(Agent):
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
        topic = message.content
        prompt = f"List exactly 3 short, factual bullet points about: {topic}. One per line, starting with '-'."
        content = self._try_llm(prompt)
        if content is None:
            topic_lower = topic.lower()
            facts = next((v for k, v in self.FACT_BANK.items() if k in topic_lower),
                         self.FACT_BANK["default"])
            content = "\n".join(f"- {f}" for f in facts)
        return Message(self.name, "orchestrator", content, msg_type="research")


class WriterAgent(Agent):
    def act(self, message: Message) -> Message:
        topic = message.metadata.get("topic", "the topic")
        research = message.metadata.get("research", "")
        feedback = message.metadata.get("feedback")

        prompt = (
            f"Write a short 4-sentence blurb about '{topic}' using these facts:\n{research}"
        )
        if feedback:
            prompt += f"\n\nIncorporate this reviewer feedback: {feedback}"

        draft = self._try_llm(prompt)
        if draft is None:
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
    Offline mode is deliberately opinionated: it always asks for one
    revision on the first pass, purely so this demo actually shows you
    the feedback loop instead of rubber-stamping everything like a
    tired manager on a Friday afternoon.
    """

    def act(self, message: Message) -> Message:
        draft = message.content
        revision_round = message.metadata.get("revision_round", 0)

        prompt = (
            "Review this draft. Reply with exactly 'APPROVED' if it's good, "
            "or 'REVISE: <one short sentence of feedback>' if it needs work.\n\n"
            f"{draft}"
        )
        response = self._try_llm(prompt)

        if response is not None:
            if response.strip().upper().startswith("APPROVED"):
                return Message(self.name, "orchestrator", "Approved.", msg_type="approval")
            feedback = response.split(":", 1)[-1].strip() if ":" in response else response
            return Message(self.name, "orchestrator", feedback, msg_type="feedback")

        # Offline fallback: always ask for one revision, then approve.
        if revision_round == 0:
            feedback = "Add a stronger closing sentence about future outlook."
            return Message(self.name, "orchestrator", feedback, msg_type="feedback")
        return Message(self.name, "orchestrator", "Approved.", msg_type="approval")


# ---------------------------------------------------------------------------
# 4. Orchestrator - wires the agents together and runs the workflow
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
        mode = "LIVE (calling Claude)" if os.environ.get("ANTHROPIC_API_KEY") else "OFFLINE (canned demo logic)"
        print(f"\n=== Starting multi-agent workflow for: '{topic}'  [mode: {mode}] ===\n")

        plan_msg = self.planner.act(Message("orchestrator", "Planner", topic))
        self._record(plan_msg)

        research_msg = self.researcher.act(Message("orchestrator", "Researcher", topic))
        self._record(research_msg)

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