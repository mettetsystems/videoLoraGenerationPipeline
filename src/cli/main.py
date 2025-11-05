from pathlib import Path
import typer
app = typer.Typer()
@app.command()
def ping(): print("ok")
if __name__ == "__main__": app()
