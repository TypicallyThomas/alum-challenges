"""
This function is tailored for synchronizing with a GitHub repository and adding
problems to the database. You can execute this function directly from the 
terminal using the following command:

python challenges/manage.py sync_problems
"""
from django.core.management.base import BaseCommand
from challenges_app.models import Challenges
from challenges_app import util
from django.db.utils import IntegrityError
import frontmatter
from glob import glob
import os
import requests
import re
import subprocess

"""
Configuration data
"""
# Files which should not be imported into the database:
OWNER = "alum-challenges"
REPO_NAME = "problems"
BRANCH_NAME = "main"
BASE_URL = "git@github.com:alum-challenges/problems.git"


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Entry point for the management command
        self.sync_problems()

    def sync_problems(self):
        """
        Synchronize problems from a GitHub repository.

        :param owner: GitHub repository owner
        :param repo_name: GitHub repository name
        :param branch_name: Branch of the repository to sync
        """

        # Use git fetch instead of downloading files
        cwd = os.getcwd()
        if not cwd.endswith("/problems"):
            prob_dir = glob(cwd + "/**/problems", recursive=True)[0]
            subprocess.run(["git", "pull"], cwd=prob_dir)
        else:
            subprocess.run(["git", "pull"])

            # Change directory to parent of problems
            os.chdir("..")

        def explore_directory():
            """
            Recursively explore the directory structure of the GitHub repository.

            :param directory_url: URL of the directory to explore
            """

            # Get all md files

            files = glob("problems/**/*.md", recursive=True)
            for file in files:
                title = file.split("/")[-1].rstrip(".md")

                # Ignore README
                if title == "README":
                    continue

                with open(file) as f:
                    problem = f.read()
                    meta = frontmatter.loads(problem).metadata

                    # Process file for our markdown
                    ## LaTeX
                    problem = problem.replace("$`", "").replace("`$", "")
                    ## Codeblocks
                    problem = re.sub(
                        r"```([^\r\n]+)", r"""```{.\1 linenums="1"}""", problem
                    )

                    challenge = util.get_challenge(title=title)

                    data = {
                        "title": title,
                        "full_title": meta.get("title", None),
                        "author": meta.get("author", None),
                        "course": meta.get("course", None),
                        "week": meta.get("week", None),
                        "topics": meta.get("topics", None),
                        "description": problem,
                    }

                    if not challenge:
                        try:
                            Challenges(**data).save()
                        except IntegrityError:
                            # Handle IntegrityError (e.g., duplicate entry) by ignoring it
                            pass
                    else:  # Update contents
                        challenge.full_title = meta.get("title", None)
                        challenge.author = meta.get("author", None)
                        challenge.course = meta.get("course", None)
                        challenge.week = meta.get("week", None)
                        challenge.topics = meta.get("topics", None)
                        challenge.description = problem
                        challenge.save(update_fields=data.keys())

        # Start exploring the directory structure from the root of the specified branch
        explore_directory()
