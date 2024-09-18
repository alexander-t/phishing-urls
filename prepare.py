import requests
from bs4 import BeautifulSoup

def get_500_popular_sites() -> list[str]:
    r = requests.get(f"https://moz.com/top500", headers={"User-agent": "Mozilla/5.0"})
    response = BeautifulSoup(r.text, "html.parser")
    return [a.attrs["href"] for a in response.find_all("a", class_="ml-2")]

if __name__ == "__main__":
    with open("top500.txt", "w") as f:
        f.writelines([f"{line}\n" for line in get_500_popular_sites()])
