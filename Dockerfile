# Your idea board in a box: the API and the page, in one image.
# Fill in the four blanks marked ____, then, from the repo root:
#     docker build -t idea-board .
#     docker run --rm -p 8000:8000 idea-board

# 1. Start from an official image that already has Python 3.13 in it.
#    Use the "slim" variant, which leaves out tools a server doesn't need.
FROM python:3.13-slim

# Everything below happens inside the image, in a folder called /app.
WORKDIR /app

# The packages the running app needs, installed before your code is copied,
# so that editing main.py doesn't reinstall them on every build.
COPY src/requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

# 2. Copy your app (main.py and web/) into /app. This file sits at the top
#    of your repo, so name the folder your app is in, with a / after it.
COPY src/ .

# A platform tells your app which port to listen on, in a variable called
# PORT. When nobody does, as on your codespace, use 8000.
ENV PORT=8000

# 3. and 4. Start the server, every time a container starts.
#    3: inside a container, 127.0.0.1 means the container itself, so listen
#       on every network interface instead.
#    4: listen on the port the platform chose. `sh -c` is what fills in a
#       $VARIABLE; the bare ["uvicorn", ...] form would pass it on as text.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port $PORT"]
