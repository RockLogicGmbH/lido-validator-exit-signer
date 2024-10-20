FROM python:3.10

WORKDIR /app
ENV PYTHONFAULTHANDLER 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# Note that poertry.lock is only used if exists
# https://stackoverflow.com/a/46801962
COPY pyproject.toml poetry.loc[k] ./

RUN POETRY_VIRTUALENVS_CREATE=false poetry install --only main --no-interaction --no-ansi

# RUN wget https://github.com/wealdtech/ethdo/releases/download/v1.35.2/ethdo-1.35.2-linux-amd64.tar.gz
# RUN tar -xzvf ethdo-1.35.2-linux-amd64.tar.gz
# RUN mv ethdo /usr/local/bin/ethdo
# RUN rm ethdo-1.35.2-linux-amd64.tar.gz

#COPY . /app
COPY templates/ /app/templates/
COPY config/ /app/config/
COPY start.sh *.py /app/
RUN poetry run pyinstaller --add-data "pyproject.toml:." --onefile --name exitsigner exitsigner.py

EXPOSE 7524
ENV __DOCKERIZED__ dockerized
#CMD ["gunicorn", "-b", "0.0.0.0:7524", "main:app"]
#CMD ["python", "main.py"]
CMD ["bash", "start.sh"]