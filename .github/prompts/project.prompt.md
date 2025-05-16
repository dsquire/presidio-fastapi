Create a FastAPI endpoint that wraps the Microsoft Presidio Analyzer for text analysis with the following requirements:

1. Implement a POST endpoint at `/analyze` that:
   - Accepts JSON payload with a "text" field containing the input string
   - Supports optional language parameter (default: "en")
   - Returns analyzed PII entities in JSON format

2. Use presidio_analyzer.AnalyzerEngine for text processing:
   - Initialize analyzer with default configuration
   - Support all default recognizer types
   - Handle errors gracefully with appropriate HTTP status codes

3. Response format:
   - Return list of detected entities with:
     * Entity type
     * Start/end positions
     * Confidence score
     * Detected text

4. Include input validation:
   - Verify text is non-empty
   - Validate language codes
   - Maximum text length limit (configurable)

5. Add proper documentation:
   - OpenAPI/Swagger annotations
   - Example request/response
   - Rate limiting headers

Reference Microsoft Presidio documentation for implementation details.