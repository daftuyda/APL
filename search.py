import requests
import json
import time
from ratelimit import limits, sleep_and_retry
from cache import cache, DEFAULT_TTL, RELATIONS_TTL

URL = "https://graphql.anilist.co"
CALLS = 85
RATE_LIMIT = 60


@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT)
def _api_request(query, variables):
    """Make a rate-limited request to AniList GraphQL API."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    response = requests.post(
        URL, json={'query': query, 'variables': variables}, headers=headers
    )

    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 5))
        time.sleep(retry_after)
        return _api_request(query, variables)

    response.raise_for_status()
    return response.json()


def fetchAllLists(username):
    """
    Fetch all anime lists for a user in a single API call.
    Returns dict of status -> list of media entries.
    Implements WIP: 'Get data with all lists'
    """
    cached = cache.get('lists', username, ttl=DEFAULT_TTL)
    if cached is not None:
        return cached

    query = """
    query($username: String, $type: MediaType) {
        MediaListCollection(userName: $username, type: $type) {
            lists {
                status
                entries {
                    media {
                        title { romaji }
                        episodes
                        duration
                        averageScore
                        format
                        status
                        id
                    }
                }
            }
        }
    }
    """

    result = _api_request(query, {"username": username, "type": "ANIME"})
    lists = result["data"]["MediaListCollection"]["lists"]

    organized = {}
    for lst in lists:
        status = lst.get("status")
        if status is None:
            continue
        if status not in organized:
            organized[status] = []
        organized[status].extend([entry["media"] for entry in lst["entries"]])

    cache.set('lists', username, organized)
    return organized


def getRelationsData(anime_id):
    """
    Fetch relation data for a single anime.
    Uses edges (not nodes) to get relation types (SEQUEL, PREQUEL, etc).
    Implements WIP: 'Add relation data for series order'
    """
    cached = cache.get('relations', str(anime_id), ttl=RELATIONS_TTL)
    if cached is not None:
        return cached

    query = """
    query($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title { romaji }
            relations {
                edges {
                    relationType
                    node {
                        id
                        type
                        format
                        status
                        title { romaji }
                    }
                }
            }
        }
    }
    """

    result = _api_request(query, {"id": anime_id})

    edges = result["data"]["Media"]["relations"]["edges"]
    relations = []
    for edge in edges:
        node = edge["node"]
        if node["type"] == "ANIME":
            relations.append({
                "id": node["id"],
                "title": node["title"]["romaji"],
                "relationType": edge["relationType"],
                "format": node["format"],
                "status": node["status"],
            })

    cache.set('relations', str(anime_id), relations)
    return relations
