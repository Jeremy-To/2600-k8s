# pod1-webapp-src/app.py
from flask import Flask, request, Response
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <h1>Web App</h1>
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
    host = request.args.get('host', '127.0.0.1')
    command = f"ping -c 1 {host}"
    
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        output = f"Command executed: '{command}'\n\nOutput:\n{result}"
    except subprocess.CalledProcessError as e:
        output = f"Command failed: '{command}'\n\nError:\n{e.output}"
    except subprocess.TimeoutExpired:
         output = f"Command timed out: '{command}'"
    except Exception as e:
        output = f"An unexpected error occurred executing '{command}':\n{str(e)}"

    return Response(output, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
