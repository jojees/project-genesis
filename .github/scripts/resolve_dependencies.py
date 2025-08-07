import os
import sys
import yaml

def resolve_dependencies(service, dependencies):
    all_services = {service}
    q = [service]
    while q:
        current_service = q.pop(0)
        for dep in dependencies.get(current_service, {}).get('needs', []):
            if dep not in all_services:
                all_services.add(dep)
                q.append(dep)
    return list(all_services)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python resolve_dependencies.py <service_name> <dependencies_file>")
        sys.exit(1)

    service_name = sys.argv[1]
    dependencies_file = sys.argv[2]
    
    with open( dependencies_file, 'r', "encoding": 'utf-8' ) as f:
        dependencies_config = yaml.safe_load(f)

    deploy_list = resolve_dependencies(service_name, dependencies_config)
    
    # Using GITHUB_OUTPUT for modern GitHub Actions
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output_file:
        print(f"services_to_deploy={','.join(deploy_list)}", file=output_file)

    print(f"Dependencies for '{service_name}': {deploy_list}")