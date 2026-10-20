from subprocess import run
import logging

def actionOnService(server, service, action):
    logging.info(f"{action}ing {service} on {server}")
    result = run(["sc", rf"\\{server}", action, f"\"{service}\""],
                 capture_output=True,
                 text=True)

    if result.returncode != 0:
        logging.error(f"Failed to {action} {service} on {server}")
    else:
        logging.info(f"Successfully {action}ed {service} on {server}")

def stopServiceOn(server, service):
    actionOnService(server, service, "stop")

def startServiceOn(server, service):
    actionOnService(server, service, "start")

def main(argv: list[str]):
    



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format=" %(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')

    