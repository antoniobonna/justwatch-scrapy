import scrapy
from scrapy_playwright.page import PageMethod


class StreamingServiceSpider(scrapy.Spider):
    """
    Spider for scraping streaming service content from JustWatch.

    This spider crawls JustWatch to collect information about movies and series
    available on different streaming platforms. It uses Playwright for handling
    dynamic content loading and infinite scrolling.

    Attributes:
        name (str): Identifier for the spider
        allowed_domains (list): Domain restriction for the crawler
        base_url (str): Base URL for building request URLs
        provedores (list): List of streaming service providers to scrape
        categoria (list): Content categories (movies/series) to scrape
    """

    name = "streaming_service"
    allowed_domains = ["www.justwatch.com"]
    base_url = "https://www.justwatch.com/br/provedor"

    # List of streaming providers to scrape
    provedores = [
        "disney-plus",
        "netflix",
        "amazon-prime-video",
        "max",
        "paramount-plus",
        "apple-tv-plus",
        "globoplay",
    ]

    # Content categories
    categoria = ["filmes", "series"]

    def start_requests(self):
        """
        Generate initial requests to start the crawling process.

        Creates request objects for each combination of provider and category,
        configuring Playwright to wait for content to load before proceeding.

        Yields:
            scrapy.Request: Request objects for each provider-category combination
        """
        for provedor in ["apple-tv-plus"]:
            for categoria in self.categoria:
                # Build the URL for this provider-category combination
                url = f"{self.base_url}/{provedor}/{categoria}"

                # Create request with Playwright configuration
                yield scrapy.Request(
                    url=url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        # Wait for content to be visible before parsing
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div.title-list-grid__item"),
                        ],
                        # Store provider and category for later use
                        "provedor": provedor,
                        "categoria": categoria,
                    },
                    callback=self.parse,
                )

    async def parse(self, response):
        """
        Parse the list page and handle infinite scrolling to load all content.

        Uses Playwright to scroll through the page, loading all dynamic content.
        Once all content is loaded, extracts links to individual items and
        yields requests to scrape detailed information.

        Args:
            response: The response object containing the page content

        Yields:
            scrapy.Request: Requests for detailed pages of each content item
        """
        # Get Playwright page object and metadata from the response
        page = response.meta["playwright_page"]
        provedor = response.meta["provedor"]
        categoria = response.meta["categoria"]

        # Configuration for infinite scroll handling
        max_scrolls = 150  # Maximum number of scroll attempts
        scroll_delay = 1500  # Wait time after each scroll (in ms)

        # Initialize item counting
        previous_item_count = 0
        scroll_count = 0

        # Get initial count of items
        items = await page.query_selector_all("div.title-list-grid__item")
        current_item_count = len(items)

        # Scroll loop: continue until no new items or max scrolls reached
        while scroll_count < max_scrolls:
            # Record current count before scrolling
            previous_item_count = current_item_count

            # Execute scroll to bottom of page
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Wait for new content to load
            await page.wait_for_timeout(scroll_delay)

            # Update item count
            items = await page.query_selector_all("div.title-list-grid__item")
            current_item_count = len(items)

            # Increment scroll counter
            scroll_count += 1

            # Check if new items were loaded
            if current_item_count == previous_item_count:
                break

        # Process all found items
        for item in items:
            # Extract item URL
            link_element = await item.query_selector("a")
            if link_element:
                href = await link_element.get_attribute("href")
                url = response.urljoin(href)

                # Create request for detail page
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_item,
                    meta={"provedor": provedor, "categoria": categoria},
                )

        # Clean up: close the Playwright page to free resources
        await page.close()

    def parse_item(self, response):
        """
        Parse individual content detail pages to extract metadata.

        Extracts title, year, duration, IMDb score, age rating, and synopsis
        from the detailed content page.

        Args:
            response: The response object containing the detail page content

        Yields:
            dict: Item containing all extracted content metadata
        """
        # Get retry count from meta or initialize to 0
        retry_count = response.meta.get("retry_count", 0)
        max_retries = 3  # Maximum number of retries for this URL

        try:
            # Extract metadata from page
            provedor = response.meta["provedor"]
            categoria = response.meta["categoria"]

            # Extract and clean content attributes
            titulo = response.css("h1.title-detail-hero__details__title::text").get()
            ano = response.css("span.release-year::text").get()

            # Handle possible missing duration
            duracao_selector = response.css("div.title-detail-hero-details__item::text")
            duracao = duracao_selector[-1].get() if duracao_selector else None

            # Extract other metadata
            imdb_score = response.css("span.imdb-score::text").get()

            # Extract age rating with XPath to navigate to text node
            classificacao = (
                response.css("#age-rating-popover")
                .xpath('./ancestor::div[@class="title-detail-hero-details__item"]/text()')
                .get()
            )

            # Extract synopsis
            sinopse = response.css("div#synopsis p::text").get()

            # Create and yield item with all extracted data
            yield {
                "provedor": provedor,
                "categoria": categoria,
                "titulo": titulo,
                "ano": ano,
                "duracao": duracao,
                "imdb_score": imdb_score,
                "classificacao": classificacao,
                "sinopse": sinopse,
                "url": response.url,
            }

        except Exception as e:
            if retry_count < max_retries:
                # Increment retry count and try again with delay
                retry_count += 1

                yield scrapy.Request(
                    url=response.url,
                    callback=self.parse_item,
                    meta={
                        "provedor": response.meta.get("provedor"),
                        "categoria": response.meta.get("categoria"),
                        "retry_count": retry_count,
                        "dont_merge_cookies": True,  # Use fresh cookies
                    },
                    dont_filter=True,  # Important: allow duplicate requests
                    priority=10,  # Higher priority for retries
                )
            else:
                # Last try, log error
                yield scrapy.Request(
                    url=response.url,
                    callback=self.parse_item,
                    meta={
                        "provedor": response.meta.get("provedor"),
                        "categoria": response.meta.get("categoria"),
                        "retry_count": retry_count,
                        "dont_merge_cookies": True,  # Use fresh cookies
                    },
                    dont_filter=True,  # Important: allow duplicate requests
                    priority=10,  # Higher priority for retries
                )
                self.logger.error(f"Error parsing {response.url}: {e}")
