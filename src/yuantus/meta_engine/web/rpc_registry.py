from typing import Callable, Dict, Any, List, Optional

# Handler signature: (engine_instance, args, kwargs) -> result
RpcHandler = Callable[[Any, List[Any], Dict[str, Any]], Any]

_registry: Dict[str, Dict[str, RpcHandler]] = {}


def rpc_exposed(model_name: str, method_name: str):
    """
    Decorator to register a method for RPC.
    Assumes the method signature is (self, args, kwargs).
    """

    def decorator(func: RpcHandler):
        _registry.setdefault(model_name, {})[method_name] = func
        return func

    return decorator


def get_handler(model: str, method: str) -> Optional[RpcHandler]:
    return _registry.get(model, {}).get(method)
