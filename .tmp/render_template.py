import json
import sys
from jinja2 import Environment, FileSystemLoader

def main():
    if len(sys.argv) != 4:
        print("Usage: python render_template.py <template_file> <config_file> <output_file>")
        sys.exit(1)
    
    template_file = sys.argv[1]
    config_file = sys.argv[2]
    output_file = sys.argv[3]
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader('.'),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Prepare context with proper structure
    context = {
        'global': config.get('global', {}),
        'clusters': config.get('clusters', {})
    }
    
    # Render template with the full context
    template = env.get_template(template_file)
    output = template.render(**context)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(output)

if __name__ == '__main__':
    main()
