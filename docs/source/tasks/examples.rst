Task Examples
===========

This guide provides examples of different task implementations in NewLoom.

Article Search Task
----------------

Example implementation of an article search task:

.. code-block:: python

    def search_articles(stream_id, url, link_selector, search_text, article_selector,
                       link_selector_type="css", article_selector_type="css", max_links=10):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = context.new_page()
            
            try:
                stealth_sync(page)
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                # Get base URL for handling relative URLs
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                # Get links using appropriate selector method
                elements = (page.query_selector_all(link_selector) 
                          if link_selector_type == "css"
                          else page.locator(f"xpath={link_selector}").all())

                matching_links = []
                for element in elements[:max_links]:
                    href = element.get_attribute("href")
                    title = element.evaluate("el => el.textContent")
                    
                    if href:
                        full_url = urljoin(base_url, href)
                        # Visit each link and search for text
                        page.goto(full_url, timeout=60000)
                        article_content = (page.query_selector(article_selector)
                                        if article_selector_type == "css"
                                        else page.locator(f"xpath={article_selector}").first)
                        
                        if article_content and search_text.lower() in article_content.text_content().lower():
                            matching_links.append({
                                "url": full_url,
                                "title": title.strip() if title else None
                            })
                            
            finally:
                browser.close()

        return matching_links

News Stream Task
-------------

Example of a news stream processing task using AI:

.. code-block:: python

    def process_news_stream(stream_id, agent_id, time_window_minutes=60, 
                          max_items=100, save_to_docs=True):
        # Get the stream and agent
        stream = Stream.objects.get(id=stream_id)
        agent = Agent.objects.get(id=agent_id)

        # Get recent news items
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        news_items = News.objects.filter(
            source__in=stream.media.sources.all(),
            created_at__gte=time_threshold
        ).order_by("-created_at")[:max_items]

        # Get examples for the media
        examples = Examples.objects.filter(media=stream.media)
        examples_text = "\n\n".join(example.text for example in examples)

        # Join news items
        news_content = "\n\n---\n\n".join(
            f"Title: {news.title}\n\nContent: {news.text}\n\nURL: {news.link}"
            for news in news_items
        )

        # Process with AI
        response = invoke_bedrock_anthropic(
            system_prompt=agent.system_prompt.format(
                news=news_content,
                examples=examples_text,
                now=timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            user_prompt=agent.user_prompt_template.format(
                news=news_content,
                examples=examples_text,
                now=timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        # Save results
        if save_to_docs:
            result = json.loads(response["completion"])
            for post in result.get("posts", []):
                Doc.objects.create(
                    media=stream.media,
                    link=post.get("url", ""),
                    title=result.get("topic", "Untitled"),
                    text=post.get("text", ""),
                    status="new"
                )

Telegram Task
-----------

Example of a Telegram channel monitoring task:

.. code-block:: python

    def monitor_telegram_channel(stream_id, posts_limit=20):
        stream = Stream.objects.get(id=stream_id)
        source = stream.source

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                stealth_sync(page)
                page.goto(source.url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                posts = []
                while len(posts) < posts_limit:
                    message_elements = page.query_selector_all(
                        "div.tgme_widget_message_wrap"
                    )

                    for message_element in message_elements:
                        # Extract message details
                        text_element = message_element.query_selector(
                            "div.tgme_widget_message_text"
                        )
                        link_element = message_element.query_selector(
                            "a.tgme_widget_message_date"
                        )
                        time_element = message_element.query_selector("time")

                        if all([text_element, link_element, time_element]):
                            message_text = text_element.inner_text().strip()
                            message_link = link_element.get_attribute("href")
                            datetime_str = time_element.get_attribute("datetime")
                            message_time = datetime.fromisoformat(
                                datetime_str.replace("Z", "+00:00")
                            )

                            # Save to database
                            News.objects.get_or_create(
                                source=source,
                                link=message_link,
                                defaults={
                                    "text": message_text,
                                    "published_at": message_time
                                }
                            )
                            posts.append({
                                "text": message_text,
                                "link": message_link,
                                "timestamp": message_time
                            })

                    # Scroll for more posts if needed
                    if len(posts) < posts_limit:
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight);"
                        )
                        page.wait_for_timeout(2000)

            finally:
                browser.close()

        return posts

Google Doc Tasks
-------------

Example of creating Google Docs from database documents:

.. code-block:: python

    def google_doc_creator(stream_id, folder_id, template_id=None, service_account_path="credentials.json"):
        # Initialize Google services
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=['https://www.googleapis.com/auth/drive.file']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        docs_service = build('docs', 'v1', credentials=credentials)

        # Get stream and docs
        stream = Stream.objects.get(id=stream_id)
        docs = Doc.objects.filter(
            status='new',
            media=stream.media,
            google_doc_link__isnull=True
        ).order_by('created_at')

        processed = 0
        failed = 0

        for doc in docs:
            try:
                if template_id:
                    # Copy template
                    file = drive_service.files().copy(
                        fileId=template_id,
                        body={'name': doc.title or "Untitled", 'parents': [folder_id]}
                    ).execute()
                else:
                    # Create new empty document
                    file = drive_service.files().create(
                        body={
                            'name': doc.title or "Untitled",
                            'mimeType': 'application/vnd.google-apps.document',
                            'parents': [folder_id]
                        }
                    ).execute()
                
                doc_id = file.get('id')
                
                # Update document content
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={
                        'requests': [{
                            'insertText': {
                                'location': {'index': 1},
                                'text': doc.text or ""
                            }
                        }]
                    }
                ).execute()
                
                # Update doc with link
                doc.google_doc_link = f"https://docs.google.com/document/d/{doc_id}/edit"
                doc.status = 'edit'
                doc.published_at = timezone.now()
                doc.save()
                
                processed += 1
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to process doc {doc.id}: {e}")
                doc.status = 'failed'
                doc.save()
                failed += 1

        return {
            "processed": processed,
            "failed": failed,
            "total": len(docs)
        }

Example of publishing Google Doc links to Telegram:

.. code-block:: python

    def telegram_doc_publisher(stream_id, message_template="{title}\n\n{google_doc_link}",
                             batch_size=10, delay_between_messages=2):
        stream = Stream.objects.get(id=stream_id)
        
        if not stream.media or not stream.media.telegram_chat_id:
            raise ValueError("Stream media must have a telegram_chat_id configured")
        
        # Get docs ready for publishing
        docs = Doc.objects.filter(
            status='edit',
            media=stream.media,
            google_doc_link__isnull=False
        ).exclude(
            id__in=TelegramDocPublishLog.objects.filter(
                media=stream.media
            ).values_list('doc_id', flat=True)
        ).order_by('created_at')[:batch_size]
        
        processed = 0
        failed = 0
        
        for doc in docs:
            try:
                # Format message
                message = message_template.format(
                    title=doc.title or "Untitled",
                    google_doc_link=doc.google_doc_link
                )
                
                # Send to Telegram
                send_telegram_message(
                    chat_id=stream.media.telegram_chat_id,
                    message=message
                )
                
                # Log publication
                TelegramDocPublishLog.objects.create(
                    doc=doc,
                    media=stream.media
                )
                
                # Update status
                doc.status = 'publish'
                doc.save()
                
                processed += 1
                
                if processed < len(docs):
                    time.sleep(delay_between_messages)
                
            except Exception as e:
                logger.error(f"Failed to publish doc {doc.id}: {e}")
                doc.status = 'failed'
                doc.save()
                failed += 1
        
        return {
            "processed": processed,
            "failed": failed,
            "total": len(docs)
        }

These examples demonstrate the current implementation patterns used in NewLoom, including:

* Playwright for web automation and scraping
* Django ORM for database operations
* Async/await patterns for Telegram operations
* Integration with AI services (Amazon Bedrock)
* Error handling and logging
* Resource cleanup

The tasks follow a consistent pattern of:
1. Getting configuration from the stream
2. Performing the main task operation
3. Saving results to the database
4. Proper error handling and cleanup
