def build_html_body(file_name: str, results: dict, synthesis_result: str) -> str:
    """
    Build the HTML body for the grading email.
    """
    return f"""
    <html>
      <body>
        <h2>📊 Transcript Grading Results: {file_name}</h2>
        <ul>
          <li><b>Discovery:</b> {results.get('discovery')}</li>
          <li><b>Value Prop:</b> {results.get('value_prop')}</li>
          <li><b>Positioning:</b> {results.get('positioning')}</li>
          <li><b>Call Control:</b> {results.get('call_control')}</li>
        </ul>
        <p><b>Summary:</b> {synthesis_result}</p>
      </body>
    </html>
    """
