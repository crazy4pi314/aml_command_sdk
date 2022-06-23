"""Creates and runs an Azure ML command job."""

import logging
from pathlib import Path

from azure.ai.ml import MLClient, Input, Output
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import (AmlCompute, Data, Environment, CommandJob,
                                  Model)

COMPUTE_NAME = "cluster-cpu"
DATA_NAME = "data-fashion-mnist"
DATA_PATH = Path(Path(__file__).parent.parent, "data")
CONDA_PATH = Path(Path(__file__).parent, "conda.yml")
CODE_PATH = Path(Path(__file__).parent.parent, "src")
MODEL_NAME = "model-command-sdk"
MODEL_PATH = Path(Path(__file__).parent.parent)


def main():
    logging.basicConfig(level=logging.INFO)
    credential = DefaultAzureCredential()
    ml_client = MLClient.from_config(credential=credential)

    # Create the compute cluster.
    logging.info("Creating the compute cluster...")
    cluster_cpu = AmlCompute(
        name=COMPUTE_NAME,
        type="amlcompute",
        size="Standard_DS4_v2",
        location="westus",
        min_instances=0,
        max_instances=4,
    )
    ml_client.begin_create_or_update(cluster_cpu)

    # Create the data set.
    logging.info("Creating the data set...")
    dataset = Data(
        path=DATA_PATH,
        type=AssetTypes.URI_FOLDER,
        description="Fashion MNIST data set",
        name=DATA_NAME,
    )
    ml_client.data.create_or_update(dataset)

    # Create the environment.
    environment = Environment(image="mcr.microsoft.com/azureml/" +
                              "openmpi4.1.0-ubuntu20.04:latest",
                              conda_file=CONDA_PATH)

    # Create the job.
    logging.info("Creating the job...")
    job = CommandJob(
        compute=COMPUTE_NAME,
        description="Trains a simple neural network on the Fashion-MNIST " +
        "dataset.",
        inputs=dict(fashion_mnist=Input(path=f"{DATA_NAME}@latest")),
        outputs=dict(model=Output(type=AssetTypes.MLFLOW_MODEL)),
        code=CODE_PATH,
        command="python train.py --data_dir ${{inputs.fashion_mnist}} " +
        "--model_dir ${{outputs.model}}",
        environment=environment,
    )
    job = ml_client.jobs.create_or_update(job)
    ml_client.jobs.stream(job.name)

    # Create the model.
    logging.info("Creating the model...")
    model_path = f"azureml://jobs/{job.name}/outputs/model"
    model = Model(path=model_path,
                  name=MODEL_NAME,
                  type=AssetTypes.MLFLOW_MODEL)
    registered_model = ml_client.models.create_or_update(model)

    # Download the model (this is optional).
    ml_client.models.download(name=MODEL_NAME,
                              download_path=MODEL_PATH,
                              version=registered_model.version)


if __name__ == "__main__":
    main()
