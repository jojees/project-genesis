#! /usr/bin/env python
import sys
import json
import yaml


def generate_overrides(changes_json, github_sha, base_values_file, output_file):
    """
    Generates a single Helm override file by starting with a base values file
    and then overriding image tags for services with source changes.
    """
    try:
        changes = json.loads(changes_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input for changes.", file=sys.stderr)
        sys.exit(1)

    # Load the base values file (e.g., values-dev.yaml)
    try:
        with open(base_values_file, 'r') as f:
            final_overrides = yaml.safe_load(f)
            if final_overrides is None: # Handle empty YAML files
                final_overrides = {}
    except FileNotFoundError:
        print(f"Warning: Base values file '{base_values_file}' not found. \
              Starting with an empty override dictionary.", file=sys.stderr)
        final_overrides = {}

    # Iterate through the services and apply overrides
    for service_name, service_changes in changes.items():
        if service_changes.get('src') == 'true':
            # Create the nested dictionary structure if it doesn't exist
            if service_name not in final_overrides:
                final_overrides[service_name] = {}
            if 'image' not in final_overrides[service_name]:
                final_overrides[service_name]['image'] = {}

            # Set the image tag to the commit SHA
            final_overrides[service_name]['image']['tag'] = github_sha

    # Write the combined overrides to the single output file
    print("Generating single Helm override file with merged values...")
    with open(output_file, 'w') as f:
        yaml.dump(final_overrides, f, sort_keys=False, default_flow_style=False)

    print(f"Override file '{output_file}' generated successfully with content:")
    with open(output_file, 'r') as f:
        print(f.read())


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python generate_helm_overrides.py <changes_json> \
              <github_sha> <base_values_file> <output_file>", file=sys.stderr)
        sys.exit(1)

    changes_json_arg = sys.argv[1]
    github_sha_arg = sys.argv[2]
    base_values_file_arg = sys.argv[3]
    output_file_arg = sys.argv[4]

    generate_overrides(changes_json_arg, github_sha_arg,
                       base_values_file_arg, output_file_arg)