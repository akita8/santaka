# Santaka


## Code generation

In order to generate protobuf and grpc code install the packages dependencies, the protoc compiler and run this commands.


### Backend

```bash
cd backend
protoc --proto_path=.. --go_out=pb --go-grpc_out=pb --go-grpc_opt=paths=source_relative --go_opt=paths=source_relative ../santaka.proto
```


### Engine

```bash
cd engine
poetry shell
python -m grpc_tools.protoc -I.. --python_out=engine --grpc_python_out=engine ../santaka.proto
```