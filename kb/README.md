# AI-300 labs: knowledge base

My personal gist of the [MicrosoftLearning/mslearn-mlops](https://github.com/MicrosoftLearning/mslearn-mlops)
labs, redone from scratch in order, the Microsoft Learn way. Each file records
what I actually ran, what broke, how it maps to the AI-300 skills measured,
and how my production project (`../MLOps_Project_Azure_ML`) does the same
thing differently.

**Environment:** one workspace provisioned in lab 01 (canadaeast, `rg-ai300-l*` /
`mlw-ai300-l*`), reused for every lab, deleted after lab 07.

**[TIMELINE.md](TIMELINE.md):** every step across all labs, in order, with who
did it and why.

**[SOURCES.md](SOURCES.md):** read before each lab: known issues from the lab docs, the repo and
Azure checks, the matching Microsoft Learn module, and where my production project covers the same ground.

**[mechanics/](mechanics/README.md):** what Azure actually does underneath, one
file per concept (workspace and storage, compute, data assets, AutoML, …).

| Lab | File | What I learned |
|---|---|---|
| 01 | [Experiment and evaluate models](01-experiment-evaluate-models.md) | AutoML found a VotingEnsemble at 0.953 accuracy (vs. 0.774 for hand-made LogisticRegression) in about 11 min on 1 node, but kept `PatientID` as a feature with every guardrail green. MLflow autolog reports *training* metrics, and saving a file isn't logging it |
| 02 | Optimize model training | _not started_ |
| 03 | Hyperparameter tuning | _not started_ |
| 04 | Run pipelines | _not started_ |
| 05 | Plan and prepare | _not started_ |
| 06 | Automate model training | _not started_ |
| 07 | Deploy and monitor | _not started_ |

## Tags

Every "lab way vs. my project" table has a **Microsoft's recommended answer**
column, and each cell is tagged:

| Tag | Meaning | On the exam |
|---|---|---|
| 🧪 | **Lab shortcut**: done this way to keep the lab short or cheap | Usually *not* the answer when a question asks for best practice |
| 📘 | **Microsoft docs recommendation**: the documented best practice | **The answer.** When the lab and current docs disagree, the docs win |
| 🛠 | **My project's own choice**: sound, but not a specific Microsoft recommendation | Valid in real life; don't pick it over a 📘 option |
