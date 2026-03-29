import os
import requests
import argparse
from pathlib import Path

def download_chess_com_pgns(username: str, output_file: Path):
    """Downloads all monthly PGN archives for a given chess.com user."""
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    
    # Chess.com API requires a User-Agent header to avoid rate limiting or blocking
    headers = {
        "User-Agent": "chess-analyst/1.0 (Personal AI Analysis Tool)"
    }
    
    print(f"Fetching archives list for user '{username}'...")
    response = requests.get(archives_url, headers=headers)
    
    if response.status_code == 404:
        print(f"Error: User '{username}' not found on chess.com.")
        return
    elif response.status_code == 403:
        print(f"Error: 403 Forbidden. The API might have blocked the request. Try adding contact info to User-Agent.")
        return
    
    response.raise_for_status()
    archives = response.json().get("archives", [])
    
    if not archives:
        print(f"No games found for user '{username}'.")
        return
    
    print(f"Found {len(archives)} monthly archives. Downloading...")

    # Ensure parent directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Track the earliest and latest months for naming
    start_month = archives[0].split('/')[-2:]
    end_month = archives[-1].split('/')[-2:]
    
    # Write all archives to a temporary file first
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for i, month_url in enumerate(archives, 1):
            pgn_url = f"{month_url}/pgn"
            year, month = month_url.split('/')[-2], month_url.split('/')[-1]
            print(f"Downloading month {i}/{len(archives)}: {year}-{month}...")
            
            pgn_response = requests.get(pgn_url, headers=headers)
            
            if pgn_response.status_code == 200:
                outfile.write(pgn_response.text)
                outfile.write("\n")
            else:
                print(f"  Warning: Failed to download {year}-{month} (Status code: {pgn_response.status_code})")
    
    # Append date range to the filename (before extension)
    date_range_suffix = f"_{start_month[0]}-{start_month[1]}_to_{end_month[0]}-{end_month[1]}"
    new_path = output_file.with_name(output_file.stem + date_range_suffix + output_file.suffix)
    output_file.rename(new_path)
    
    print(f"\nDone! Successfully downloaded all games to:")
    print(f"  {new_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download all PGNs for a chess.com user")
    parser.add_argument("username", help="Chess.com username")
    parser.add_argument("--output", "-o", help="Output PGN file path", default=None)
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default to data/raw/<username>_games.pgn in the project root
        project_root = Path(__file__).parent.parent
        output_path = project_root / "data" / "raw" / f"{args.username}_games.pgn"
        
    download_chess_com_pgns(args.username, output_path)
