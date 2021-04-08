import fastapi
import pydantic
import requests
import typing
import uvicorn
import os

app = fastapi.APIRouter()

class DataModel(pydantic.BaseModel):
    repo: str
    branch: typing.Optional[str] = "master"

@app.post("/clone")
def download_gh_repo(data: DataModel = fastapi.Body(...), x_gh_token: typing.Optional[str] = fastapi.Header(None)):
    file_path = dl_github_repo(data.repo, x_gh_token or None, data.branch)
    if file_path is None:
        raise fastapi.exceptions.HTTPException(404, "Repo not found")
    return fastapi.responses.FileResponse(file_path)


def dl_github_repo(repo: str, token: typing.Optional[str] = None, branch="master"):
    folder = repo.split("/")[0]
    file = repo.split("/")[1]

    if token is not None:
        headers = {"Authorization": "token " + token}
    else:
        headers = None
    res = requests.get(f"https://github.com/{repo}/archive/refs/heads/{branch}.tar.gz", headers=headers)
    
    if res.status_code != 200:
        return None
    if not os.path.exists("repos"):
        os.mkdir("repos")
    if not os.path.exists("repos/" + folder):
        os.mkdir("repos/" + folder)
    path = f"repos/{folder}/{file}.tar.gz"
    with open(path, "wb") as f:
        f.write(res.content)

    return path
