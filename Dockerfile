# Main image for running things in a Django/Python environment.
FROM python:3.7-buster

# Configuration defaults
ENV ODDSLINGERS_ROOT "/opt/oddslingers.poker"
ENV DATA_DIR "$ODDSLINGERS_ROOT/data"
ENV HTTP_PORT "8000"
ENV DJANGO_USER "www-data"
ENV VENV_NAME ".venv-docker"
ENV NODE_MAJOR "18"
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Use archived Debian sources for Buster
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until && \
    sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/|http://archive.debian.org/|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
        python-psycopg2 libpq-dev \
        fish \
        npm \
        gosu \
        build-essential \
        python3-dev python3-pip python3-venv jq \
        supervisor && \
    rm -rf /var/lib/apt/lists/*

# Node.js keyring setup
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
RUN apt-get update && apt-get install -y nodejs

# Setup Python virtualenv separately from code dir
WORKDIR "$ODDSLINGERS_ROOT"
RUN pip install virtualenv && virtualenv "$VENV_NAME"
ENV PATH="$ODDSLINGERS_ROOT/$VENV_NAME/bin:${ODDSLINGERS_ROOT}/bin:./node_modules/.bin:${PATH}"

# Git metadata
ADD .git/HEAD ./.git/HEAD
ADD .git/refs/heads/ ./.git/refs/heads/

# Install Python dependencies
COPY ./core/Pipfile.lock "$ODDSLINGERS_ROOT/Pipfile.lock"
RUN jq -r '.default,.develop | to_entries[] | .key + .value.version' "$ODDSLINGERS_ROOT/Pipfile.lock" | \
    pip install --no-cache-dir -r /dev/stdin && \
    rm "$ODDSLINGERS_ROOT/Pipfile.lock"

# Install npm and yarn
RUN npm install --global npm && npm install --global yarn

# Setup Django user
RUN userdel "$DJANGO_USER" && addgroup --system "$DJANGO_USER" && \
    adduser --system --ingroup "$DJANGO_USER" --shell /bin/false "$DJANGO_USER"

# Setup app directories
RUN mkdir -p "$ODDSLINGERS_ROOT/data/logs" "$ODDSLINGERS_ROOT/core/js/node_modules"
RUN chown -R "$DJANGO_USER:$DJANGO_USER" "$ODDSLINGERS_ROOT/data" "$ODDSLINGERS_ROOT/data/logs" "$ODDSLINGERS_ROOT/core"

ENTRYPOINT [ "/opt/oddslingers.poker/bin/entrypoint.sh" ]

