import scrapy
from scrapy_playwright.page import PageMethod


class StreamingServiceSpider(scrapy.Spider):
    name = "streaming_service"
    allowed_domains = ["www.justwatch.com"]
    base_url = "https://www.justwatch.com/br/provedor/"
    provedores = [
        "disney-plus",
        "netflix",
        "amazon-prime-video",
        "max",
        "paramount-plus",
        "apple-tv-plus",
        "globoplay",
    ]

    # filmes ou series
    categoria = [
        "filmes",
        "series"
    ]

    def start_requests(self):
        for provedor in self.provedores:
            for categoria in self.categoria:
                yield scrapy.Request(
                    url=f"{self.base_url}{provedor}/{categoria}",
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div.title-list-grid__item"),
                        ],
                    },
                    callback=self.parse,
                )

    def parse(self, response):
        pass
