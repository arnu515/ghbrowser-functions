import fastapi
import subprocess
import pydantic
import requests
import typing
import uvicorn
import os

app = fastapi.APIRouter()

class DataModel(pydantic.BaseModel):
    repo: str
    branch: typing.Optional[str] = "master"

async def extract_github_repo_background_task(data, file_path: str, folder_path: str, post_url: typing.Optional[str], io_url: typing.Optional[str] = None):
    async for i in extract_github_repo(file_path, folder_path):
        if i.get("main"):
            continue
        if post_url:
            if i.get("is_folder"):
                requests.post(post_url, {**data.dict(), **i, "path": None})
            else:
                with open(i["path"], "rb") as f:
                    requests.post(post_url, {**data.dict(), **i, "path": None}, files={"file": f})

@app.get("/clone")
def download_gh_repo(repo: str = fastapi.Query(...), branch: typing.Optional[str] = fastapi.Query("master"), x_gh_token: typing.Optional[str] = fastapi.Header(None)):
    file_path, _folder_path = dl_github_repo(repo, x_gh_token or None, branch)
    if file_path is None:
        raise fastapi.exceptions.HTTPException(404, "Repo not found")
    return fastapi.responses.FileResponse(file_path)

@app.post("/clone")
def download_gh_repo(tasks: fastapi.BackgroundTasks, post_url: typing.Optional[str] = fastapi.Query(None), io_url: typing.Optional[str] = fastapi.Query(None), tar: typing.Optional[str] = fastapi.Query(None), data: DataModel = fastapi.Body(...), x_gh_token: typing.Optional[str] = fastapi.Header(None)):
    file_path, folder_path = dl_github_repo(data.repo, x_gh_token or None, data.branch)
    if file_path is None:
        raise fastapi.exceptions.HTTPException(404, "Repo not found")
    tasks.add_task(extract_github_repo_background_task, data, file_path, folder_path, post_url, io_url)

    return fastapi.responses.FileResponse(file_path) if tar is not None else data.repo


def dl_github_repo(repo: str, token: typing.Optional[str] = None, branch="master"):
    folder = repo.split("/")[0]
    file = repo.split("/")[1]
    basepath = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(basepath, "repos", folder, file + ".tar.gz")
    if os.path.exists(path):
        return path, os.path.join(basepath, "repos", folder)

    if token is not None:
        headers = {"Authorization": "token " + token}
    else:
        headers = None
    res = requests.get(f"https://github.com/{repo}/archive/refs/heads/{branch}.tar.gz", headers=headers)
    
    if res.status_code != 200:
        return None, None
    if not os.path.exists(os.path.join(basepath, "repos")):
        os.mkdir(os.path.join(basepath, "repos"))
    if not os.path.exists(os.path.join(basepath, "repos", folder)):
        os.mkdir(os.path.join(basepath, "repos", folder))
    with open(path, "wb") as f:
        f.write(res.content)
    return path, os.path.join(basepath, "repos", folder)

async def extract_github_repo(path: str, folder_path: str):
    contents = subprocess.Popen("cd " + folder_path + " && tar -xvzf " + path, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().split("\n")[0:-1]
    folder = contents.pop(0)[0:-1] # gets the first item, removes it from the list, and removes the trailing slash.
    yield {"name":folder, "is_folder": True, "main": True}
    for i in contents:
        is_folder = i.endswith("/")
        yield {"name": i, "is_folder": is_folder, "path": os.path.join(folder_path, i)}
