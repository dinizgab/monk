from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
    
class CLIPrinter():
    def __init__(self):
        self.console = Console()
    
    def print_execution_plan(self, data):
        self.console.rule("[bold blue]Execution Plan")

        table = Table(show_header=True)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Description")

        for step in data.execution_plan:
            table.add_row(str(step.id), step.description)

        self.console.print(table)
        self.console.rule()
        
    def saved_to(self, path: str | Path, label: str = "Saved to"):
        p = Path(path).resolve()
        self.console.print(Panel.fit(f"[bold]{label}[/bold]\n{p}", border_style="green"))