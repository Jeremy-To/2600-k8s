# pod1-webapp-src/app.py
from flask import Flask, request, Response
import os
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <h1>Web App (Pod 1)</h1>
    <p>Try the ping tool:</p>
    <form action="/ping" method="get">
      <label for="host">Host to ping:</label>
      <input type="text" id="host" name="host" value="127.0.0.1">
      <input type="submit" value="Ping">
    </form>
    <p>Example vulnerability trigger: <code>/ping?host=127.0.0.1; id</code></p>
    """

@app.route('/ping')
def ping():
    host = request.args.get('host', '127.0.0.1') # Default to localhost if no host is provided
    
    # --- VULNERABILITY: Command Injection ---
    # Using os.system or similar functions with unsanitized input is dangerous
    # command = f"ping -c 1 {host}" 
    # For demonstration, we'll use something more direct to show injection
    command = host # Directly execute the input 'host' parameter value
    
    try:
        # Execute the command. 
        # NOTE: In a real scenario, NEVER run user input directly like this.
        # Using shell=True is also highly risky with untrusted input.
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        output = f"Command executed: '{command}'\n\nOutput:\n{result}"
    except subprocess.CalledProcessError as e:
        output = f"Command failed: '{command}'\n\nError:\n{e.output}"
    except subprocess.TimeoutExpired:
         output = f"Command timed out: '{command}'"
    except Exception as e:
        output = f"An unexpected error occurred executing '{command}':\n{str(e)}"

    return Response(output, mimetype='text/plain')

# Route to demonstrate sudo python execution
@app.route('/runpy')
def run_python_script():
    script_path = "/app/utility.py" # A placeholder script
    # Create a dummy script if it doesn't exist
    if not os.path.exists(script_path):
        with open(script_path, "w") as f:
            f.write("import os\nprint(f'Running as UID: {os.geteuid()}, GID: {os.getegid()}')\n")
            f.write("print('This script could potentially do more...')\n")
        os.chmod(script_path, 0o755) # Make it executable

    # --- VULNERABILITY: Potential abuse of sudo NOPASSWD ---
    command = f"sudo /usr/bin/python3 {script_path}"
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=10)
        output = f"Executing privileged Python script: '{command}'\n\nOutput:\n{result}"
    except Exception as e:
        output = f"Failed to execute privileged script: '{command}'\nError: {str(e)}"
    
    return Response(output, mimetype='text/plain')


if __name__ == '__main__':
    # Make sure the app runs as a non-root user later in the Dockerfile
    # For now, run on 0.0.0.0 to be accessible within the container network
    app.run(host='0.0.0.0', port=5000) 
