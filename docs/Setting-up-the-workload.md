# Setting up the Docker Containers for Triton Server and Client

In this step, we will set up Docker containers for the Triton server and client, and configure the example model repository.

## 1. **Run Triton Server in Docker**

  To begin, clone the `server` repository to get the example model repository and set it up.
  
  ```bash
  git clone -b r24.08 https://github.com/triton-inference-server/server.git
  cd server/docs/examples
```

## 2. **Fetch the Models**

  Run the script to fetch the models:
  
  ```bash
  ./fetch_models.sh
  ```
  If the script fails, change the download link from [here](https://github.com/triton-inference-server/server/pull/7621/files) and run it again.

## 3. **Run Triton Server in Docker**

  Now, run the Triton server in a Docker container. Make sure that the model repository is correctly mapped to the container. Run the following command from inside the `server/docs/examples`:
  
  ```bash
  docker run -it --net=host --pid=host --name=triton-server -v ${PWD}/model_repository:/models nvcr.io/nvidia/tritonserver:24.08-py3 tritonserver --model-repository=/models
  ```
  
  This will start the Triton server and load the models from the model_repository.

## 4. **Verify Triton Server is Running**

  After starting the server, you should see logs in the terminal indicating that the Triton server has successfully started. The server should now be running and ready to serve the models.

## 5. **Run Triton Client in Docker**

  To interact with the Triton server, you need the Triton client. Pull the Docker image for the Triton SDK:

  ```bash
  docker pull nvcr.io/nvidia/tritonserver:24.08-py3-sdk
  ```

  Once the image is pulled, run the Triton client in Docker:

  ```bash
  docker run -it --net=host --pid=host --name=triton-client -v ${PWD}/server/docs/examples/model_repository:/models nvcr.io/nvidia/tritonserver:24.08-py3-sdk
  ```
  This command starts the Triton client, allowing it to interact with the server running on your system.


