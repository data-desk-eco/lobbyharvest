import click
import csv
import json
from src.scrapers import lobbyfacts

@click.group()
def cli():
    pass

@cli.command()
@click.option('--firm-name', '-f', required=True, help='Name of the lobbying firm (e.g. "FTI Consulting Belgium")')
@click.option('--url', '-u', help='Direct URL to the firm\'s Lobbyfacts page')
@click.option('--output', '-o', default='output.csv', help='Output file path (default: output.csv)')
@click.option('--format', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
def lobbyfacts_scrape(firm_name, url, output, format):
    click.echo(f"Scraping Lobbyfacts for {firm_name}...")

    clients = lobbyfacts.scrape_lobbyfacts(firm_name, url)

    if not clients:
        click.echo("No clients found.")
        return

    click.echo(f"Found {len(clients)} clients")

    if format == 'csv':
        with open(output, 'w', newline='') as f:
            if clients:
                writer = csv.DictWriter(f, fieldnames=clients[0].keys())
                writer.writeheader()
                writer.writerows(clients)
    else:
        with open(output, 'w') as f:
            json.dump(clients, f, indent=2)

    click.echo(f"Results saved to {output}")

def main():
    cli()

if __name__ == "__main__":
    main()
