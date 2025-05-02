import json

import scrapy
from scrapy.exceptions import CloseSpider


class StreamingServiceSpider(scrapy.Spider):
    """
    Spider for scraping streaming service content from JustWatch.

    This spider crawls JustWatch to collect information about movies and series
    available on different streaming platforms.  It uses the JustWatch GraphQL
    API to retrieve data.

    Attributes:
        name (str): Identifier for the spider
        allowed_domains (list): Domain restriction for the crawler
        api_url (str): Base URL for the GraphQL API
        provedores (list): List of streaming service providers to scrape
        categoria (list): Content categories (movies/series) to scrape
    """

    name = "streaming_service_api"
    allowed_domains = ["apis.justwatch.com"]

    # Base URL for the GraphQL API
    api_url = "https://apis.justwatch.com/graphql"

    # List of streaming providers to scrape
    providers = [
        "dnp",  # Disney+
        "nfx",  # Netflix
        "prv",  # Amazon Prime Video
        "mxx",  # Max (formerly HBO Max)
        "pmp",  # Paramount+
        "atp",  # Apple TV+
        "gop",  # Globoplay
    ]

    # Content categories
    categories = ["filmes", "series"]

    def start_requests(self):
        """
        Generate initial requests to start the crawling process.

        This method constructs GraphQL queries for each provider and category
        combination and yields corresponding Scrapy Request objects.  The initial
        offset for each query is set to 0.

        Yields:
            scrapy.Request:  GraphQL POST requests for each provider and category.
        """
        for provider in ["prv"]:
            for category in ["filmes"]:
                # Determine the object type based on the category
                object_type = "MOVIE" if category == "filmes" else "SHOW"

                # Prepare the GraphQL query payload
                json_data = {
                    "operationName": "GetPopularTitles",
                    "variables": {
                        "first": 40,
                        "popularTitlesSortBy": "POPULAR",
                        "sortRandomSeed": 0,
                        "offset": 0,
                        "country": "BR",
                        "language": "pt",
                        "popularTitlesFilter": {
                            "objectTypes": [object_type],
                            "packages": [provider],
                        },
                    },
                    "query": """
                    query GetPopularTitles($country: Country!, $first: Int!, $popularTitlesSortBy: PopularTitlesSorting!, 
                                          $language: Language!, $sortRandomSeed: Int!, $offset: Int!, 
                                          $popularTitlesFilter: TitleFilter!) {
                      popularTitles(
                        country: $country
                        sortBy: $popularTitlesSortBy
                        first: $first
                        sortRandomSeed: $sortRandomSeed
                        offset: $offset
                        filter: $popularTitlesFilter
                      ) {
                        edges {
                          node {
                            id
                            content(country: $country, language: $language) {
                              title
                              fullPath
                            }
                          }
                        }
                      }
                    }
                    """,
                }

                # Yield the initial request for the title list
                yield scrapy.Request(
                    url=self.api_url,
                    method="POST",
                    body=json.dumps(json_data),
                    callback=self.parse_title_list,
                    meta={
                        "provider": provider,
                        "category": category,
                        "json_data": json_data,
                        "offset": 0,  # Start with offset 0
                    },
                )

    async def parse_title_list(self, response):
        """
        Parse the title list response from the GraphQL API and handle pagination.

        This method extracts title information from the API response,
        and yields requests for the detail pages of each title.  It also
        handles pagination by incrementing the offset and making subsequent
        requests to the API.

        Args:
            response (scrapy.http.Response): The API response.

        Yields:
            scrapy.Request:  Requests for the detail pages of each title.
        """
        # Extract metadata from the response
        provider = response.meta["provider"]
        category = response.meta["category"]
        json_data = response.meta["json_data"]
        current_offset = response.meta["offset"]

        # Parse the JSON response
        data = response.json()

        # Access the list of titles
        edges = data.get("data", {}).get("popularTitles", {}).get("edges", [])

        # Check if the page is empty
        if not edges:
            return  # Stop processing

        for item in edges:
            node = item.get("node", {})
            content = node.get("content", {})
            path = content.get("fullPath")

            if path:
                # Prepare the GraphQL query for title details
                details_json_data = {
                    "operationName": "GetUrlTitleDetails",
                    "variables": {
                        "fullPath": path,
                        "language": "pt",
                        "country": "BR",
                    },
                    "query": """
                    query GetUrlTitleDetails($fullPath: String!, $country: Country!, $language: Language!) {
                    urlV2(fullPath: $fullPath) {
                        heading1
                        node {
                        ... on MovieOrShowOrSeason {
                            content(country: $country, language: $language) {
                            originalReleaseYear
                            runtime
                            shortDescription
                            scoring {
                                imdbScore
                                imdbVotes
                            }
                            ... on MovieOrShowContent {
                                ageCertification
                            }
                            }
                        }
                        }
                    }
                    }
                    """,
                }

                # Yield a request for the title details page
                yield scrapy.Request(
                    url=self.api_url,
                    method="POST",
                    body=json.dumps(details_json_data),
                    callback=self.parse_title_details,
                    meta={"provider": provider, "category": category, "path": path},
                )

        # Increment the offset for the next page
        next_offset = current_offset + 40
        json_data["variables"]["offset"] = next_offset

        # Make the next request with the updated offset
        yield scrapy.Request(
            url=self.api_url,
            method="POST",
            body=json.dumps(json_data),
            callback=self.parse_title_list,
            meta={
                "provider": provider,
                "category": category,
                "json_data": json_data,
                "offset": next_offset,
            },
        )

    def parse_title_details(self, response):
        """
        Parse the GraphQL API response to extract content metadata.

        Extracts title, year, runtime, IMDb score, age rating, and synopsis
        from the API response.

        Args:
            response (scrapy.http.Response): The API response.

        Yields:
            dict: Item containing all extracted content metadata
        """
        try:
            # Parse JSON response
            data = response.json()

            # Extract metadata from the response.meta
            provider = response.meta["provider"]
            category = response.meta["category"]
            path = response.meta["path"]

            # Navigate the response structure to get the desired data
            node_data = data.get("data", {}).get("urlV2", {})
            content = node_data.get("node", {}).get("content", {})

            # Extract information
            title = node_data.get("heading1")
            year = content.get("originalReleaseYear")
            runtime = content.get("runtime")
            imdb_score = content.get("scoring", {}).get("imdbScore")
            imdb_count = content.get("scoring", {}).get("imdbVotes")
            classification = content.get("ageCertification")
            synopsis = content.get("shortDescription")

            # Create and yield item with all extracted data
            yield {
                "provedor": provider,
                "categoria": category,
                "titulo": title,
                "ano": year,
                "duracao_minutos": runtime,
                "imdb_score": imdb_score,
                "imdb_count": imdb_count,
                "classificacao": classification,
                "sinopse": synopsis,
                "url": f"https://www.justwatch.com{path}",
            }

        except Exception as e:
            self.logger.error(f"Error parsing API response for {response.meta.get('path')}: {e}")
