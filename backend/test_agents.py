"""
test_agents.py

Run this BEFORE building the frontend, and before wiring main.py.
The goal is to catch prompt/parsing bugs here, in isolation, rather than
debugging them through a browser and a fetch call at the same time.

Run with:
    python test_agents.py
"""

from agents import context_agent, diagnostic_agent, exemplar_agent, rewrite_agent

SAMPLE_JOB_DESCRIPTION = """
The Glencore 2026 Commodities Spring Week 
We are looking for proactive, driven first year university students who are interested in the world of commodities trading to join us for a three-day Spring Week in early April (from April 13 – 15, 2026).  
This is a unique opportunity to gain exposure into the world of commodities trading, learning about the day-to-day work of our traders, analysts, and risk managers through presentations, practical case studies and networking opportunities. 
You will receive professional skills training and interview guidance, helping you to prepare for a fast-paced career upon graduation. 
Candidates who are successful in the application process for the Spring Week will be able to take part in an accelerated application process for an industrial placement or graduate programme.
"""

SAMPLE_QUESTION = """
"What do you want to gain from taking part in a Spring Week at Glencore?"
"""

SAMPLE_DRAFT_ANSWER = """
First, I've built strong quantitative skills through AI and maths, and I'm confident I can analyse data, build models, and think systematically. But I don't yet have exposure to applying those skills under pressure, with real money, in fast-moving markets. Ultimately, I want to better understand what “good” decision making looks like on a trading desk and how my technical skillset could add value in a commodities context. 
Second, I want to understand how commodities markets work beyond what you can learn from books. I'm curious about how physical supply chains interact with the markets, how traders manage risk when prices move based on weather, strikes, or geopolitics, and how much of trading is disciplined analysis versus reading situations in real time. I am excited to see the case studies and shadowing which will give me that ground-level view. 

Third, commercial awareness. Right now, my understanding of how businesses operate, how stakeholders think, and how markets respond to events is mostly theoretical. Whether I end up in trading, tech, or elsewhere, that's a gap I need to close early. 
"""


def main():
    print("Testing context_agent...")
    brief = context_agent(SAMPLE_JOB_DESCRIPTION, SAMPLE_QUESTION)
    print(brief.model_dump_json(indent=2))

    print("\nTesting diagnostic_agent...")
    diagnostic = diagnostic_agent(brief, SAMPLE_DRAFT_ANSWER)
    print(diagnostic.model_dump_json(indent=2))

    print("\nTesting exemplar_agent...")
    exemplars = exemplar_agent(diagnostic.flags)
    print(exemplars)

    print("\nTesting rewrite_agent...")
    rewrites = rewrite_agent(diagnostic.flags, exemplars)
    print(rewrites)


if __name__ == "__main__":
    main()
