# Online endpoints: scoring scripts, rollout and rollback

Started after practice questions [Q37 + Q39](../../practice/q037-q039-online-endpoint-basics.md).
My production project runs this for real (`ml/score/score.py`, `deploy.yml`,
`shift-traffic.yml`); this note puts it in exam terms.

## Endpoint vs. deployment

- **Endpoint:** a stable URL, auth (key or token), and a **traffic split**.
- **Deployment:** one model version + scoring code + environment + instances,
  behind the endpoint (`blue`, `green`).

## The scoring (entry) script

```python
def init():          # once, when the container starts → load the model
    global model
    model = mlflow.sklearn.load_model(os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model"))

def run(raw_data):   # once per request → score and return
    data = pd.DataFrame(json.loads(raw_data)["data"])
    return model.predict(data).tolist()
```

- Exam cue: "load when the service starts" → `init()`; "score new data" →
  `run()`. Not `main`, `score` or `predict`.
- **No-code MLflow deployments** need no scoring script; Azure ML generates
  one.
- **Batch** scoring scripts also use `init()`, but `run(mini_batch)` gets a
  **list of files**, not a JSON request.

## Safe rollout and rollback

1. Deploy `green` beside `blue` at **0% traffic**.
2. Test it directly (`--deployment-name green`).
3. Optionally **mirror** traffic (shadow) or shift a small %.
4. Shift 100% to `green`.
5. Keep `blue` until confident.

**Rollback** = shift traffic back to the previous deployment. That's the
fastest fix after a bad release. Deleting and redeploying the endpoint is
slow; changing auth or compute size doesn't address a bad release.

## No outbound internet: package the model

From practice question [Q49](../../practice/q049-package-model-no-egress.md).

- A **no-code MLflow** deployment installs the model's conda/pip
  dependencies **when the container starts**. That needs internet.
- If the endpoint's outbound access is blocked, first create a **model
  package**: an image with the model and all its dependencies built in. Then
  deploy the package.
- Neither a registry nor a private endpoint fixes it: the first shares
  assets, the second secures inbound traffic.

## Online vs. batch endpoints

From practice question [Q57](../../practice/q053-q054-q056-q057-quick-ones.md).

| | **Online (real-time)** | **Batch** |
|---|---|---|
| Call pattern | Synchronous request → response | Asynchronous **job** over files/folders |
| Latency | Milliseconds | Minutes to hours |
| Volume | One or a few records per call | Millions of records |
| Compute | Always-on instances (managed) | A compute **cluster**, only while the job runs |
| Typical cue | "during customer interactions" | "files", "nightly/scheduled", "large volume" |

A safe test of a new version on live users = **traffic splitting** between
deployments on the **same** endpoint ([Q54](../../practice/q053-q054-q056-q057-quick-ones.md)),
not a separate staging endpoint.
