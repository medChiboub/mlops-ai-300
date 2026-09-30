from azure.identity import DefaultAzureCredential
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    DataCollector,
    DeploymentCollection,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
)
from azure.core.exceptions import ResourceNotFoundError

import argparse
import os


def get_data_collector() -> DataCollector:
    return DataCollector(
        collections={
            "model_inputs": DeploymentCollection(enabled="true"),
            "model_outputs": DeploymentCollection(enabled="true"),
        }
    )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--subscription-id", dest="subscription_id", required=True)
    parser.add_argument("--resource-group", dest="resource_group", required=True)
    parser.add_argument("--workspace", dest="workspace", required=True)
    parser.add_argument("--endpoint-name", dest="endpoint_name", default="diabetes-endpoint")
    parser.add_argument("--model-name", dest="model_name", default="diabetes-model")
    parser.add_argument("--model-version", dest="model_version", default=None,
                        help="registered version to deploy; default: latest")
    parser.add_argument("--deployment-name", dest="deployment_name", default=None,
                        help="default: v<model version>")
    parser.add_argument("--request-file", dest="request_file", default="sample-request.json")

    return parser.parse_args()


def get_ml_client(subscription_id: str, resource_group: str, workspace: str) -> MLClient:
    credential = DefaultAzureCredential()
    return MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace,
    )


def ensure_endpoint(ml_client: MLClient, endpoint_name: str) -> ManagedOnlineEndpoint:
    try:
        return ml_client.online_endpoints.get(name=endpoint_name)
    except ResourceNotFoundError:
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description="Online endpoint for MLflow diabetes model",
            auth_mode="key",
        )
        return ml_client.online_endpoints.begin_create_or_update(endpoint).result()


def get_registered_model(ml_client: MLClient, model_name: str, model_version: str):
    if model_version:
        return ml_client.models.get(name=model_name, version=model_version)
    return ml_client.models.get(name=model_name, label="latest")


def create_or_update_deployment(
    ml_client: MLClient,
    endpoint_name: str,
    deployment_name: str,
    model,
) -> ManagedOnlineDeployment:
    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=model.id,
        instance_type="Standard_D2as_v4",
        instance_count=1,
        data_collector=get_data_collector(),
    )

    return ml_client.online_deployments.begin_create_or_update(deployment).result()


def smoke_test(ml_client: MLClient, endpoint_name: str, deployment_name: str, request_file: str) -> str:
    # call the new deployment directly, before it receives any traffic
    return ml_client.online_endpoints.invoke(
        endpoint_name=endpoint_name,
        deployment_name=deployment_name,
        request_file=request_file,
    )


def set_traffic_to_deployment(ml_client: MLClient, endpoint_name: str, deployment_name: str) -> dict:
    # new deployment gets 100%; previous deployments stay deployed at 0% for rollback
    endpoint = ml_client.online_endpoints.get(name=endpoint_name)
    existing = ml_client.online_deployments.list(endpoint_name=endpoint_name)
    traffic = {d.name: 0 for d in existing}
    traffic[deployment_name] = 100
    endpoint.traffic = traffic
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    return traffic


def write_github_outputs(**values) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            for key, value in values.items():
                f.write(f"{key}={value}\n")


def main() -> None:
    args = parse_args()

    print("Connecting to Azure Machine Learning workspace...")
    ml_client = get_ml_client(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        workspace=args.workspace,
    )

    print(f"Ensuring online endpoint '{args.endpoint_name}' exists...")
    endpoint = ensure_endpoint(ml_client, args.endpoint_name)
    print(f"Using endpoint: {endpoint.name}")

    model = get_registered_model(ml_client, args.model_name, args.model_version)
    deployment_name = args.deployment_name or f"v{model.version}"
    print(f"Deploying registered model {model.name}:{model.version} as deployment '{deployment_name}'...")
    deployment = create_or_update_deployment(
        ml_client=ml_client,
        endpoint_name=endpoint.name,
        deployment_name=deployment_name,
        model=model,
    )
    print(f"Deployment state: {deployment.provisioning_state}")

    print(f"Smoke test: invoking '{deployment_name}' directly with {args.request_file}...")
    response = smoke_test(ml_client, endpoint.name, deployment_name, args.request_file)
    print(f"Smoke test response: {response}")

    print(f"Directing 100% of traffic to '{deployment_name}'...")
    traffic = set_traffic_to_deployment(ml_client, endpoint.name, deployment_name)

    endpoint = ml_client.online_endpoints.get(name=endpoint.name)
    print(f"Deployment complete. Traffic: {traffic}. Scoring URI: {endpoint.scoring_uri}")

    write_github_outputs(
        model_version=model.version,
        deployment_name=deployment_name,
        traffic=" ".join(f"{k}={v}" for k, v in traffic.items()),
        smoke_test=str(response).replace("\n", " "),
    )


if __name__ == "__main__":
    main()
