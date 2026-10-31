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
