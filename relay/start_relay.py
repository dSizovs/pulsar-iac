import os
import threading
import time
import asyncio
import uvicorn
from pulsar_relay.main import app

os.environ["PULSAR_JWT_SECRET_KEY"] = "super_secret_dev_key"

def inject_admin():
    time.sleep(2)
    print("\n" + "="*50)
    print(">>> INJECTING PRIVILEGED ADMIN...")
    try:
        from pulsar_relay.auth.models import UserCreate
        import pulsar_relay.auth.dependencies as deps

        storage = getattr(deps, "user_storage", getattr(deps, "_user_storage", None))

        if storage:
            user = UserCreate(
                username="admin", 
                password="password", 
                email="admin@example.com",
                permissions=["admin", "read", "write"]
            )
            asyncio.run(storage.create_user(user))
            print(">>> PRIVILEGED ADMIN INJECTED SUCCESSFULLY! <<<")
        else:
            print(">>> ERROR: Could not find user_storage!")
    except Exception as e:
        print(f">>> ERROR: {e}")
    print("="*50 + "\n")

if __name__ == "__main__":
    threading.Thread(target=inject_admin, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=9000)
