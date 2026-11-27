<?xml version="1.0" encoding="utf-8"?>
<!--
  Renders /feed.xml as a readable page when a person opens it in a browser.
  Feed readers ignore this file.

  Chrome removed XSLT in November 2026, so Chrome shows the raw XML instead.
  The same entries are on the /feed page, which works in every browser; the
  banner below points there.
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:xhtml="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="atom xhtml">

  <xsl:output method="html" encoding="utf-8" indent="yes" doctype-system="about:legacy-compat" />

  <xsl:template match="/atom:feed">
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="robots" content="noindex" />
        <title><xsl:value-of select="atom:title" /> (feed)</title>
        <style>
          :root {
            color-scheme: light dark;
            --surface: #fcfcfb; --page: #f9f9f7; --text: #0b0b0b;
            --text-2: #52514e; --muted: #6b6a65;
            --border: rgba(11, 11, 11, 0.10); --accent: #2a78d6;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --surface: #171a1f; --page: #0d1014; --text: #ffffff;
              --text-2: #c3c2b7; --muted: #9a978f;
              --border: rgba(255, 255, 255, 0.10); --accent: #3987e5;
            }
          }
          * { box-sizing: border-box; }
          body {
            margin: 0; background: var(--page); color: var(--text);
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            -webkit-font-smoothing: antialiased;
          }
          main { max-width: 760px; margin: 0 auto; padding: 32px 16px 48px; }
          a { color: var(--accent); }
          .eyebrow { font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-2); margin: 0 0 6px; }
          h1 { font-size: 28px; margin: 0 0 10px; line-height: 1.2; }
          .lede { color: var(--text-2); line-height: 1.5; margin: 0 0 16px; }
          .howto {
            background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
            padding: 14px 16px; font-size: 14px; color: var(--text-2); line-height: 1.5; margin-bottom: 24px;
          }
          .howto code {
            font-size: 13px; padding: 1px 6px; border-radius: 6px;
            background: var(--page); border: 1px solid var(--border);
            display: inline-block; overflow-wrap: anywhere;
          }
          article {
            background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
            padding: 16px 18px; margin-bottom: 12px;
          }
          h2 { font-size: 16px; margin: 0 0 8px; }
          article p, article li { font-size: 14px; color: var(--text-2); line-height: 1.6; }
          article p { margin: 0 0 6px; }
          article p:last-child { margin-bottom: 0; }
          article ul { margin: 0 0 8px; padding-left: 20px; }
          article strong { color: var(--text); font-weight: 600; }
        </style>
      </head>
      <body>
        <main>
          <p class="eyebrow"><a href="/">All banks</a> / Feed</p>
          <h1><xsl:value-of select="atom:title" /></h1>
          <p class="lede"><xsl:value-of select="atom:subtitle" /></p>
          <div class="howto">
            This is an Atom feed. To follow it, copy this address into a feed reader:
            <code><xsl:value-of select="atom:link[@rel='self']/@href" /></code>.
            The same entries are also on the <a href="/feed">daily rates page</a>.
          </div>
          <xsl:apply-templates select="atom:entry" />
        </main>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="atom:entry">
    <article>
      <h2><a href="{atom:link/@href}"><xsl:value-of select="atom:title" /></a></h2>
      <xsl:apply-templates select="atom:content/xhtml:div/node()" mode="copy" />
    </article>
  </xsl:template>

  <!-- Copy the entry's XHTML into the output as plain HTML elements. -->
  <xsl:template match="xhtml:*" mode="copy">
    <xsl:element name="{local-name()}">
      <xsl:copy-of select="@*" />
      <xsl:apply-templates select="node()" mode="copy" />
    </xsl:element>
  </xsl:template>

  <xsl:template match="text()" mode="copy">
    <xsl:value-of select="." />
  </xsl:template>
</xsl:stylesheet>
