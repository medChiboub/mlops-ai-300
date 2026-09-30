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

**[mechanics/](mechanics/README.md):** what Azure actually does underneath, one
file per concept (workspace and storage, compute, data assets, AutoML, …).

| Lab | File | What I learned |
|---|---|---|
| 01 | [Experiment and evaluate models](01-experiment-evaluate-models.md) | AutoML found a VotingEnsemble at 0.953 accuracy (vs. 0.774 for hand-made LogisticRegression) in about 11 min on 1 node, but kept `PatientID` as a feature with every guardrail green. MLflow autolog reports *training* metrics, and saving a file isn't logging it |
| 02 | [Optimize model training](02-optimize-model-training.md) | A Studio export is just the cells pasted into one file; the refactored script takes arguments. A command job records code snapshot + data + environment + logs, which a terminal run doesn't (that one went to `Default`). The same code gave a different AUC in the job because the environment pins scikit-learn 1.0. Autolog adds 15 params, `training_*` metrics and the `model/` folder |
| 03 | Hyperparameter tuning | _not started_ |
| 04 | Run pipelines | _not started_ |
| 05 | Plan and prepare | _not started_ |
| 06 | Automate model training | _not started_ |
| 07 | Deploy and monitor | _not started_ |

## AI-300 coverage (MLOps domains)

Skills measured from the [AI-300 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-300)
(checked 2026-09-29). These labs only cover **Domain 1 (15–20%)** and
**Domain 2 (25–30%)**. **Domains 3–5 (GenAIOps / Microsoft Foundry, about
45–55% of the exam) aren't in any lab or in my production project.**

Updated after each lab. **Labs** = the labs whose docs cover the skill.
**Status** = what I've done so far in these labs.
**Prod** = my production project (from its `docs/AI-300.md`).

Status: ✅ done · 👀 seen but not done · ⚠ partial or failed · ⏳ planned in a later lab · ❌ no lab covers it

### Domain 1: Design and implement an MLOps infrastructure (15–20%)

| Skill | Labs | Status | Prod |
|---|---|---|---|
| Create and manage a workspace | 01 (CLI), 05 (dev/prod design) | ✅ 01 | ✅ |
| Create and manage datastores | none creates one | 👀 01: the 4 defaults | ✅ |
| Create and manage compute targets | 01 | ✅ 01 | ✅ |
| Configure identity and access for workspaces | 06 (service principal, RG scope), 07 (environment secrets) | ⏳ | ✅ |
| Create and manage data assets | 01 (uri_file, MLTable), 07 (uri_folder dev/prod) | ✅ 01 | ✅ |
| Create and manage environments | 02/03 *use* a curated one; none creates one | 👀 02: used curated `sklearn-1.0` (and saw it change results) | ✅ |
| Create and manage components | 04 | ⏳ | ✅ |
| Share assets across workspaces with registries | 05 (design; optional create) | ⏳ | ✅ |
| Configure GitHub integration for secure access | 06, 07 | ⏳ | ✅ (OIDC) |
| Deploy workspaces and resources with Bicep and Azure CLI | 01 (CLI); **no Bicep in any lab** | ⚠ 01: CLI half | ✅ |
| Automate provisioning with GitHub Actions | ❌ (05 only mentions it) | ❌ | ✅ |
| Restrict network access to workspaces | 06 (read-only review) | ⏳ | ❌ |
| Manage source control with Git | 06, 07 (branches, PRs, branch protection) | ⏳ | ✅ |

### Domain 2: Implement ML model lifecycle and operations (25–30%)

| Skill | Labs | Status | Prod |
|---|---|---|---|
| Configure experiment tracking with MLflow | 01, 02 | ✅ 01, 02 | ✅ |
| Use AutoML to explore optimal models | 01 | ✅ 01 | ✅ |
| Use notebooks for experimentation | 01 | ✅ 01 | ✅ |
| Automate hyperparameter tuning | 03 | ⏳ | ✅ |
| Run model training scripts | 02, 06 | ✅ 02 | ✅ |
| Manage distributed training | ❌ | ❌ | ❌ |
| Implement training pipelines | 04 | ⏳ | ✅ |
| Compare model performance across jobs | 01, 02, 07 (dev vs. prod metrics) | ✅ 01, 02 | ✅ |
| Package a feature retrieval specification with the model | ❌ | ❌ | ❌ |
| Register an MLflow model | 07 (only *implicitly*, through deployment) | ⏳ | ✅ |
| Evaluate a model with responsible AI principles | 01 (module text only); optional notebook `Create Responsible AI dashboard.ipynb` | ⚠ 01: automatic `_RAI` run failed | ⚠ |
| Manage model lifecycle, including archiving | 07 (optional rollback step) | ⏳ | ✅ |
| Deploy real-time or batch endpoints | 07 (real-time only) | ⏳ | ✅ both |
| Test and troubleshoot endpoints | 07 | ⏳ | ✅ |
| Progressive rollout and safe rollback | 07 (optional) | ⏳ | ✅ |
| Detect and analyze data drift | 07 (needs about a day of traffic) | ⏳ | ⚠ |
| Monitor performance metrics in production | 07 (partly) | ⏳ | ❌ |
| Configure retraining or alert triggers | 07 (simulated by hand) | ⏳ | ❌ |

**Gaps no lab and no prod work covers:** distributed training, feature
retrieval specifications, restricting network access (beyond a read-only
review), and automated retraining or alert triggers. Study these from the
docs.

## Tags

Every "lab way vs. my project" table has a **Microsoft's recommended answer**
column, and each cell is tagged:

| Tag | Meaning | On the exam |
|---|---|---|
| 🧪 | **Lab shortcut**: done this way to keep the lab short or cheap | Usually *not* the answer when a question asks for best practice |
| 📘 | **Microsoft docs recommendation**: the documented best practice | **The answer.** When the lab and current docs disagree, the docs win |
| 🛠 | **My project's own choice**: sound, but not a specific Microsoft recommendation | Valid in real life; don't pick it over a 📘 option |
