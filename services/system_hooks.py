import docker
from datetime import datetime
from utils.logger import get_logger
from models.database import SystemHook, get_session

logger = get_logger("mastarr.hooks")


class SystemHooks:
    """Execute system lifecycle hooks"""

    def __init__(self):
        self.client = docker.from_env()

    async def create_mastarr_network(self):
        """
        First run: Create custom Docker network.
        Replicates MESS's first_run_up.sh network creation.
        """
        logger.info("Creating mastarr network...")

        try:
            network = self.client.networks.get("mastarr_net")
            logger.info("✓ mastarr_net already exists")
            return network

        except docker.errors.NotFound:
            network = self.client.networks.create(
                name="mastarr_net",
                driver="bridge",
                ipam=docker.types.IPAMConfig(
                    pool_configs=[
                        docker.types.IPAMPool(
                            subnet="10.21.12.0/26",
                            gateway="10.21.12.1"
                        )
                    ]
                ),
                labels={"created_by": "mastarr"}
            )
            logger.info("✓ mastarr_net created with subnet 10.21.12.0/26")
            return network

    async def connect_mastarr_to_network(self):
        """
        Every run: Connect mastarr container to network.
        Replicates MESS's run_up.sh network connection.
        """
        logger.info("Connecting mastarr to network...")

        try:
            container = self.client.containers.get("mastarr")
            network = self.client.networks.get("mastarr_net")

            container.reload()
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})

            if "mastarr_net" in networks:
                logger.info("✓ Already connected to mastarr_net")
                return

            network.connect(container, ipv4_address="10.21.12.2")
            logger.info("✓ Connected to mastarr_net at 10.21.12.2")

        except docker.errors.NotFound as e:
            logger.error(f"Container or network not found: {e}")
        except Exception as e:
            logger.error(f"Failed to connect to network: {e}")
            raise

    async def disconnect_mastarr_from_network(self):
        """
        Teardown: Disconnect from network.
        Replicates MESS's run_down.sh network disconnection.
        """
        logger.info("Disconnecting mastarr from network...")

        try:
            container = self.client.containers.get("mastarr")
            network = self.client.networks.get("mastarr_net")
            network.disconnect(container)
            logger.info("✓ Disconnected from mastarr_net")

        except docker.errors.NotFound:
            logger.warning("Container or network not found, skipping disconnect")
        except Exception as e:
            logger.warning(f"Could not disconnect: {e}")


def get_hooks(hook_type: str = None, executed: bool = None):
    """
    Get system hooks from database.

    Args:
        hook_type: Filter by hook type (first_run_only, every_run, teardown)
        executed: Filter by execution status (for first_run_only hooks)

    Returns:
        List of SystemHook objects
    """
    db = get_session()
    query = db.query(SystemHook).filter(SystemHook.enabled == True)

    if hook_type:
        query = query.filter(SystemHook.hook_type == hook_type)

    if executed is not None:
        query = query.filter(SystemHook.executed == executed)

    hooks = query.order_by(SystemHook.execution_order).all()
    db.close()
    return hooks


def mark_hook_executed(hook_name: str):
    """
    Mark a hook as executed.

    Args:
        hook_name: Name of the hook
    """
    db = get_session()
    hook = db.query(SystemHook).filter(SystemHook.name == hook_name).first()

    if hook:
        hook.executed = True
        hook.last_executed = datetime.utcnow()
        db.commit()
        logger.info(f"Marked hook as executed: {hook_name}")

    db.close()


def initialize_system_hooks():
    """
    Initialize default system hooks in database.
    Should be called once during first setup.
    """
    db = get_session()

    default_hooks = [
        {
            "name": "create_network",
            "hook_type": "first_run_only",
            "function_name": "create_mastarr_network",
            "execution_order": -1
        },
        {
            "name": "connect_to_network",
            "hook_type": "every_run",
            "function_name": "connect_mastarr_to_network",
            "execution_order": 0
        },
        {
            "name": "disconnect_from_network",
            "hook_type": "teardown",
            "function_name": "disconnect_mastarr_from_network",
            "execution_order": 998
        }
    ]

    for hook_data in default_hooks:
        existing = db.query(SystemHook).filter(
            SystemHook.name == hook_data["name"]
        ).first()

        if not existing:
            hook = SystemHook(**hook_data)
            db.add(hook)
            logger.info(f"Created system hook: {hook_data['name']}")

    db.commit()
    db.close()
