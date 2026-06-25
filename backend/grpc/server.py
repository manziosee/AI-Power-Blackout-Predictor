"""gRPC server for SCADA / enterprise integrations.

Generate stubs first:
  pip install grpcio-tools
  python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. blackout.proto

Then run:
  python -m app.grpc.server
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_HOST = "0.0.0.0"
_PORT = 50051


def _check_stubs() -> bool:
    try:
        import grpc  # noqa: F401
        return True
    except ImportError:
        return False


async def serve() -> None:
    """Start the gRPC server (stubs must be generated from blackout.proto)."""
    if not _check_stubs():
        logger.error("grpcio not installed — cannot start gRPC server")
        return

    import grpc
    from grpc import aio

    try:
        import blackout_pb2 as pb2  # type: ignore
        import blackout_pb2_grpc as pb2_grpc  # type: ignore
    except ImportError:
        logger.error(
            "Proto stubs not found. Run: "
            "python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. blackout.proto"
        )
        return

    class PredictionServicer(pb2_grpc.PredictionServiceServicer):
        async def GetPrediction(self, request, context):
            return pb2.PredictionResponse(
                h3_index=request.h3_index,
                probability=0.0,
                risk_level="unknown",
                window_start=datetime.now(timezone.utc).isoformat(),
                window_end=datetime.now(timezone.utc).isoformat(),
                model_version="grpc-stub",
            )

        async def StreamPredictions(self, request, context):
            for h3 in request.h3_indexes:
                yield pb2.PredictionResponse(
                    h3_index=h3,
                    probability=0.0,
                    risk_level="unknown",
                    window_start=datetime.now(timezone.utc).isoformat(),
                    window_end=datetime.now(timezone.utc).isoformat(),
                    model_version="grpc-stub",
                )

    class GridLoadServicer(pb2_grpc.GridLoadServiceServicer):
        async def PushSnapshot(self, request, context):
            logger.info(
                "gRPC GridSnapshot received: region=%s load_mw=%.2f",
                request.region,
                request.load_mw,
            )
            return pb2.SnapshotAck(accepted=True, id=str(uuid.uuid4()))

    server = aio.server()
    pb2_grpc.add_PredictionServiceServicer_to_server(PredictionServicer(), server)
    pb2_grpc.add_GridLoadServiceServicer_to_server(GridLoadServicer(), server)
    server.add_insecure_port(f"{_HOST}:{_PORT}")
    await server.start()
    logger.info("gRPC server listening on %s:%s", _HOST, _PORT)
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
