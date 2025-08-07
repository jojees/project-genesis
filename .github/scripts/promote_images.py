#! /usr/bin/env python
import subprocess
import argparse
import logging
import sys
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def promote_images(override_file, github_sha, docker_org, deployment_namespace):
    logging.info(f"Starting image promotion for namespace: {deployment_namespace}")
    
    # Load the override file
    try:
        with open(override_file, 'r') as f:
            overrides = yaml.safe_load(f)
        if overrides is None:
            overrides = {}
            logging.warning("Override file is empty.")
    except FileNotFoundError:
        logging.error(f"Override file '{override_file}' not found.")
        return 1

    promoted_services_count = 0
    # Iterate through each service in the override file
    for service_name, service_config in overrides.items():
        # Check for the specific condition to promote
        if 'image' in service_config and 'tag' in service_config['image'] and service_config['image']['tag'] == github_sha:
            
            source_image = f"{docker_org}/{service_name}:{github_sha}"
            target_tag = f"{deployment_namespace}"
            target_image = f"{docker_org}/{service_name}:{target_tag}"
            
            logging.info(f"Attempting to promote {source_image} to {target_image}")
            
            try:
                # Docker pull
                logging.info(f"Pulling {source_image}...")
                subprocess.run(['docker', 'pull', source_image], check=True, stdout=sys.stdout, stderr=sys.stderr)
                
                # Docker tag
                logging.info(f"Tagging {source_image} as {target_image}...")
                subprocess.run(['docker', 'tag', source_image, target_image], check=True, stdout=sys.stdout, stderr=sys.stderr)
                
                # Docker push
                logging.info(f"Pushing {target_image}...")
                subprocess.run(['docker', 'push', target_image], check=True, stdout=sys.stdout, stderr=sys.stderr)
                
                logging.info(f"Successfully promoted {service_name}.")
                promoted_services_count += 1
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to promote {service_name}. Error: {e}")
                return 1 # Exit with an error code

    if promoted_services_count == 0:
        logging.info("No services found with a matching SHA tag to promote.")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Promote Docker images after a successful Helm deployment.')
    parser.add_argument('--override-file', required=True, help='Path to the Helm override YAML file.')
    parser.add_argument('--github-sha', required=True, help='The GitHub commit SHA.')
    parser.add_argument('--docker-org', required=True, help='The Docker organization/username.')
    parser.add_argument('--namespace', required=True, help='The target namespace for the new image tag.')
    
    args = parser.parse_args()
    
    exit_code = promote_images(args.override_file, args.github_sha,
                               args.docker_org, args.namespace)
    sys.exit(exit_code)