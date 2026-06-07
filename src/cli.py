import typer
from rich.console import Console
from rich.table import Table
from ytmusicapi import YTMusic

import src.archive as archive_db
import src.releases as releases_db
from src.archive import Artist


app = typer.Typer(help="Youtube Music Artist -> New Releases URL", no_args_is_help=True)
console = Console()
yt = YTMusic()


@app.command()
def add(query: str = typer.Argument(help="Artist name to search for")):
    """Search for an artist and add them to the following list."""
    console.print(f"\nSearching for [bold]{query}[/bold]...")
    results = yt.search(query, filter="artists")

    if not results:
        console.print("[red]No artists found.[/red]")
        raise typer.Exit(1)

    top = results[:5]

    table = Table("", "Name", "Browse ID", show_header=True, header_style="bold")
    for i, r in enumerate(top, 1):
        table.add_row(
            str(i),
            r.get("artist") or r.get("title", "Unknown"),
            r.get("browseId") or "",
        )
    console.print(table)

    raw = typer.prompt("Select artist", default="1")
    try:
        selected = top[int(raw) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)

    artist = Artist(
        name=selected.get("artist") or selected.get("title", "Unknown"),
        browse_id=selected["browseId"],
        releases=[],
    )

    if archive_db.add(artist):
        console.print(f"\n[green]Now following:[/green] {artist.name} ([dim]{artist.browse_id}[/dim])")
        check(artist.name)
    else:
        console.print(f"\n[yellow]Already following:[/yellow] {artist.name}")
        archived = archive_db.load_artist(artist.browse_id)
        if archived.releases == []:
            check(artist.name)

@app.command()
def remove(query: str = typer.Argument(help="Artist name or browse ID")):
    """Remove an artist from the following list."""
    archive = archive_db.load_archive()

    if not archive:
        console.print("[yellow]No artists followed yet.[/yellow]")
        raise typer.Exit()

    needle = query.lower().strip()
    matches = [
        a for a in archive
        if needle in a.name.lower()
        or needle == a.browse_id.lower()
    ]

    if not matches:
        console.print(f"[red]No artist matching '{query}' found.[/red]")
        raise typer.Exit(1)

    if len(matches) > 1:
        table = Table("", "Name", "Browse ID", show_header=True, header_style="bold")
        for i, a in enumerate(matches, 1):
            table.add_row(str(i), a.name, a.browse_id)
        console.print(table)

        raw = typer.prompt("Select artist to remove", default="1")
        try:
            selected = matches[int(raw) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")
            raise typer.Exit(1)
    else:
        selected = matches[0]

    if typer.confirm(f"Remove {selected.name}?"):
        archive_db.remove(selected.browse_id)
        console.print(f"[green]Removed:[/green] {selected.name}")
    else:
        console.print("Cancelled.")


@app.command(name="list")
def list_artists():
    """List all followed artists."""
    archive = archive_db.load_archive()

    if not archive:
        console.print("[yellow]No artists followed yet. Use 'add' to get started.[/yellow]")
        return

    table = Table("Name", "Browse ID", show_header=True, header_style="bold")
    for a in archive:
        table.add_row(a.name, a.browse_id)

    console.print(table)
    console.print(f"\n[dim]{len(archive)} artist(s) followed.[/dim]")


@app.command()
def check(query: str = typer.Argument(help="Artist name or browse ID")):
    """Check for new releases for one artist and manually select them."""
    archive = archive_db.load_archive()

    if not archive:
        console.print("[yellow]No artists followed yet.[/yellow]")
        raise typer.Exit()

    needle = query.lower().strip()
    matches = [
        a for a in archive
        if needle in a.name.lower()
        or needle == a.browse_id.lower()
    ]

    if not matches:
        console.print(f"[red]No artist matching '{query}' found.[/red]")
        raise typer.Exit(1)

    if len(matches) > 1:
        table = Table("", "Name", "Browse ID", show_header=True, header_style="bold")
        for i, a in enumerate(matches, 1):
            table.add_row(str(i), a.name, a.browse_id)
        console.print(table)

        raw = typer.prompt("Select artist", default="1")
        try:
            artist = matches[int(raw) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")
            raise typer.Exit(1)
    else:
        artist = matches[0]

    download_urls: list[str] = []
    untrack_urls: list[str] = []
    console.print(f"\n[bold]{artist.name}[/bold]")
    
    try:
        new_releases = releases_db.get_new_releases(artist.browse_id)
    except RuntimeError as e:
        console.print(f"  [red]{e}[/red]")
        return
        
    if not new_releases:
        console.print("  [dim]No new releases.[/dim]")
        return
        
    total_new = len(new_releases)

    table = Table("", "Type", "Title", "Year", "URL", show_header=True, header_style="bold")
    for i, r in enumerate(new_releases, 1):
        table.add_row(
            str(i),
            r.get("category"),
            r.get("title"),
            r.get("year"),
            r.get("url"),
        )
    console.print(table)
    console.print(f"\n[dim]{total_new} new release(s).[/dim]")

    all_indices = list(range(len(new_releases)))
    selection = typer.prompt("Release(s) to download (all | 1 2 4 7)", default="all")
    try:
        if selection.strip().lower() == "all":
            download_indices = all_indices
        else:
            download_indices = [int(x) - 1 for x in selection.split()]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)

    for i in download_indices:
        download_urls.append(new_releases[i]["url"])

    other_indices = [i for i in all_indices if i not in download_indices]
    selection = typer.prompt("Release(s) to untrack (others | 1 2 4 7 | none)", default="others")
    try:
        if selection.strip().lower() == "none":
            untrack_indices = []
        elif selection.strip().lower() == "others":
            untrack_indices = other_indices
        else:
            untrack_indices = [int(x) - 1 for x in selection.split()]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)

    for i in untrack_indices:
        untrack_urls.append(new_releases[i]["url"])

    console.print()
    if untrack_urls:
        archive_db.add_releases(artist.browse_id, untrack_urls)
        console.print(f"[bold green]{len(untrack_urls)} release(s) untracked.[/bold green]")
    if download_urls:
        console.print(f"[bold green]{len(download_urls)} release(s) to download.[/bold green]")
        for url in download_urls:
            console.print(url)
        if typer.confirm("Have you downloaded all release(s)?"):
            archive_db.add_releases(artist.browse_id, download_urls)
    if not download_urls and not untrack_urls:
        console.print("[dim]Nothing to do.[/dim]")


@app.command()
def sync():
    """Check for new releases for all artists and manually select them."""
    archive = archive_db.load_archive()

    if not archive:
        console.print("[yellow]No artists in list.[/yellow]")
        return
    
    for artist in archive:
        check(artist.name)
