# AI-native Memory 2.0: Second Me

**Authors:** Jiale Wei, Xiang Ying, Tao Gao, Fangyi Bao, Felix Tao, Jingbo Shang

**Publication:** Mindverse.ai

---

# AI-native Memory 2.0: Second Me

## 1. Title, Authors, and Publication Details
*   **Title:** AI-native Memory 2.0: Second Me
*   **Authors:** Jiale Wei, Xiang Ying, Tao Gao, Fangyi Bao, Felix Tao, Jingbo Shang (Mindverse.ai)
*   **Publication:** arXiv:2503.08102v2 \[cs.AI], 12 Mar 2025 (Preprint, Under Review)

## 2. Research Questions/Objectives
*   How can Large Language Models (LLMs) be leveraged to create an AI-native personal memory system that intelligently retains, organizes, and utilizes user-specific knowledge?
*   How can such a system (SECOND ME) act as a dynamic intermediary in human-machine interactions, reducing cognitive load and improving efficiency?
*   What data sources and training styles (SFT, DPO, CoT) are most effective for training a personal LLM for tasks like memory-based Q&A, context enhancement, and context critique?

## 3. Methodology Used
*   **Hybrid Architecture:** A three-layer system (L0: Raw Data, L1: Natural Language Memory, L2: AI-Native Memory) with inner and outer loops for seamless integration and interaction with external resources.
*   **Automated Training Pipeline:** Data synthesis (LLM-driven, local/global perspectives, multi-agent framework, Chain-of-Thought), filtering, Supervised Fine-Tuning (SFT), Direct Preference Optimization (DPO), and automated evaluation.
*   **Training Data Synthesis:** LLMs were used to generate data for Memory QA, Context Enhancement, and Context Critic tasks.
*   **Answer Style Experimentation:** Explored Weak, Multi-step, and Strong Chain-of-Thought (CoT) strategies.
*   **Evaluation:** Automated evaluation using metrics like Memory (Self/Third-Party), Context Enhance, and Context Critic. Human case studies were also conducted.

## 4. Key Findings and Results
*   Strong Chain-of-Thought (CoT) significantly improves model performance in memory-related questions and expert communication.
*   Multi-step CoT often fails to meet user needs, highlighting the importance of well-structured training data.
*   Direct Preference Optimization (DPO) brings substantial improvements, with iterative CoT refinement and DPO usage leading to consistent performance gains across all tasks.
*   Human evaluation suggests SECOND ME's effectiveness may surpass reported metrics, as LLM-based evaluations tend to underestimate its quality.

## 5. Main Conclusions and Implications
*   SECOND ME represents a new paradigm for personalized LLM applications, acting as an intelligent, persistent memory offload system.
*   It reduces cognitive effort by preemptively providing relevant information, auto-completing forms, recalling past interactions, and maintaining context across applications.
*   It has the potential to facilitate networked intelligence, where multiple agents collaborate, share relevant insights, and coordinate tasks across different applications and users.
*   The key to enabling humans to fully integrate into AGI lies in an AI system that stands on the user’s side—one that considers each individual, possesses their memory, and has absorbed it meaningfully.

## 6. Limitations Mentioned in the Paper
*   Early work relied on single-turn training, requiring deeper synthesis for further advancements.
*   Refining model alignment demands more advanced techniques than reinforcement learning and preference optimization alone.
*   Large-scale evaluation is constrained by limited real-world user feedback.
*   Evaluation model favors longer responses, particularly in metrics like Completeness and Empathy.
*   Achieving real-time synchronization with human thought remains elusive.
