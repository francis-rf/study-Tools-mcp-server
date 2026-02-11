// API base URL
const API_BASE = "";

// Load files on page load
window.addEventListener("DOMContentLoaded", () => {
  loadFiles();

  // Enter key to send message
  document.getElementById("user-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});

// Load available study materials
async function loadFiles() {
  try {
    const response = await fetch(`${API_BASE}/api/files`);
    const data = await response.json();

    const filesList = document.getElementById("files-list");

    if (data.files && data.files.length > 0) {
      filesList.innerHTML = data.files
        .map((file) => `<div class="file-item" title="${file}">${file}</div>`)
        .join("");
    } else {
      filesList.innerHTML =
        '<div class="file-item">No files found. Add PDFs or Markdown files to data/notes/</div>';
    }
  } catch (error) {
    console.error("Error loading files:", error);
    document.getElementById("files-list").innerHTML =
      '<div class="file-item">Error loading files</div>';
  }
}

// Send message to the API
async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();

  if (!message) return;

  // Clear input
  input.value = "";

  // Add user message to chat
  addMessage(message, "user");

  // Disable send button
  const sendBtn = document.getElementById("send-btn");
  sendBtn.disabled = true;
  sendBtn.textContent = "Thinking...";

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error("Failed to get response");
    }

    // Read streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessage = "";

    // Create assistant message container
    const messageDiv = addMessage("", "assistant");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();

          if (data === "[DONE]") {
            break;
          }

          assistantMessage += data + "\n";
          // During streaming: show plain text only (no flashcard/quiz rendering yet)
          messageDiv.innerHTML = formatMessage(assistantMessage, true);

          // Auto-scroll to bottom
          messageDiv.scrollIntoView({ behavior: "smooth", block: "end" });
        }
      }
    }

    // After streaming is complete: do the final render with flashcard/quiz support
    messageDiv.innerHTML = formatMessage(assistantMessage, false);
  } catch (error) {
    console.error("Error:", error);
    addMessage("❌ Error: " + error.message, "system");
  } finally {
    // Re-enable send button
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

// Add message to chat
function addMessage(text, type) {
  const messagesDiv = document.getElementById("messages");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}`;
  messageDiv.innerHTML = formatMessage(text);
  messagesDiv.appendChild(messageDiv);

  // Auto-scroll to bottom
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  return messageDiv;
}

// Format message with basic markdown-like styling
// streamingMode=true: still receiving data, skip interactive components
function formatMessage(text, streamingMode) {
    if (!text) return '';

    // During streaming, just show plain text with minimal formatting
    if (streamingMode) {
        let plain = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        plain = plain.replace(/\n/g, '<br>');
        return plain;
    }

    // === AFTER STREAMING IS DONE: full interactive rendering ===

    // --- JSON path: try to parse as structured quiz/flashcard data first ---
    try {
        const trimmed = text.trim();
        if (trimmed.startsWith("{")) {
            const parsed = JSON.parse(trimmed);
            if (Array.isArray(parsed.questions) || Array.isArray(parsed.quiz)) {
                console.log("Detected structured quiz JSON, rendering from JSON");
                return renderQuizFromJSON(parsed);
            }
            if (Array.isArray(parsed.cards) || Array.isArray(parsed.flashcards)) {
                console.log("Detected structured flashcards JSON, rendering from JSON");
                return renderFlashcardsFromJSON(parsed);
            }
        }
    } catch (e) {
        // Not valid JSON — fall through to regex / markdown path
    }

    // --- Regex fallback path (legacy) ---

    // Check if this looks like a quiz response (has specific patterns)
    const hasQuestions = /Question\s*\d+|^\d+\.\s+/im.test(text);
    const hasOptions = /[A-D][\.\)]\s+/m.test(text);

    console.log("Quiz Detection:", { hasQuestions, hasOptions, textLength: text.length });

    // If it looks like a quiz, try to render it interactively
    if (hasQuestions && hasOptions) {
        console.log("Attempting to render interactive quiz...");
        try {
            const result = renderInteractiveQuiz(text);
            console.log("Interactive quiz rendered successfully");
            return result;
        } catch (e) {
            console.error("Failed to render interactive quiz:", e);
            console.log("Falling back to standard formatting");
        }
    } else {
        console.log("Not detected as quiz, using standard formatting");
    }

    // Check if this is a flashcard format and render interactively
    // Strip bold markers before testing so "**Card 1**\n**Front:**" is detected
    if (/Card\s+\d+[\s*]*Front:/i.test(text.replace(/\*\*/g, ''))) {
        return renderInteractiveFlashcards(text);
    }

    // === USE MARKED.JS FOR STANDARD MARKDOWN PARSING ===
    try {
        // Pre-process: Prevent "Setext" headers where "---" turns previous text into a giant header
        // If "---" follows text directly, insert a newline
        text = text.replace(/([^\n])\n\s*---\s*\n/g, '$1\n\n---\n');

        // Configure marked options
        marked.setOptions({
            breaks: false, // Standard markdown: only \n\n creates paragraph breaks
            gfm: true      // Enable GitHub Flavored Markdown
        });

        // Collapse 3+ consecutive newlines into 2 (one blank line max)
        text = text.replace(/\n{3,}/g, '\n\n');

        // Parse markdown
        let html = marked.parse(text);

        // Add 'user-content-' class to headings to avoid css conflicts if needed, 
        // or just rely on .message.assistant descendent selectors which is better.
        
        // Post-processing for specific interactive elements like "Show Answers" button if needed
        // but robust markdown usually handles headers well.
        
        // Hide answers section with a button (custom feature)
        // We look for the "Answers" header generated by marked (usually h3 or h4)
        const answersRegex = /<h[34][^>]*>(Answers|Answers and Explanations|Answers:)<\/h[34]>/i;
        const answersMatch = html.match(answersRegex);
        
        if (answersMatch) {
            const splitIndex = html.indexOf(answersMatch[0]);
            if (splitIndex > -1) {
                const beforeAnswers = html.substring(0, splitIndex);
                const afterAnswers = html.substring(splitIndex);
                
                html = beforeAnswers +
                       '\n\n<div style="text-align: center; margin: 30px 0;"><button class="toggle-answers-btn" onclick="toggleAnswers(this)">Show Answers</button></div>\n' +
                       '<div class="answers-content">\n' +
                       afterAnswers +
                       '\n</div>';
            }
        }

        return html;

    } catch (e) {
        console.error("Error parsing markdown:", e);
        return text; // Fallback
    }
}

function renderInteractiveQuiz(text) {
    console.log("=== renderInteractiveQuiz called ===");
    console.log("Input text length:", text.length);
    console.log("First 200 chars:", text.substring(0, 200));
    console.log("Last 300 chars:", text.substring(text.length - 300));
    
    // 1. Identify split between Questions and Answers
    // Strategy: find the first standalone "---" that is followed (possibly after blank lines)
    // by "Question X Answer:" — that's the canonical separator the prompt requests.
    // Also support headers like "### Answers" as a fallback.
    let questionText = text;
    let answerText = "";

    // Try: standalone --- (possibly with surrounding whitespace) before answer block
    const separatorMatch = text.match(/^([\s\S]*?)\n---+\s*\n([\s\S]*?Question\s+\d+\s+Answer:[\s\S]*)$/im);
    if (separatorMatch) {
        questionText = separatorMatch[1];
        answerText = separatorMatch[2];
        console.log("Split via --- separator at char", questionText.length);
    } else {
        // Fallback: header-based split
        const headerMatch = text.match(/([\s\S]*?)(####+\s*Answers?[\s\S]*|Answers?\s+and\s+Explanations[\s\S]*)/i);
        if (headerMatch) {
            questionText = headerMatch[1];
            answerText = headerMatch[2];
            console.log("Split via header at char", questionText.length);
        } else {
            // Last resort: first occurrence of "Question X Answer:"
            const lastResort = text.match(/^([\s\S]*?)(Question\s+\d+\s+Answer:[\s\S]*)$/im);
            if (lastResort) {
                questionText = lastResort[1];
                answerText = lastResort[2];
                console.log("Split via first 'Question X Answer:' at char", questionText.length);
            } else {
                console.log("No answer section found, treating entire text as questions");
            }
        }
    }
    console.log("Answer section preview:", answerText.substring(0, 150));

    // 2. Parse Answers to build a lookup map
    const answerMap = {};
    const explanationMap = {};
    
    if (answerText) {
        console.log("Parsing answers...");
        // Match "Question X Answer: Y" format
        const answerRegex = /Question\s+(\d+)\s+Answer:\s*([A-D])\b/gi;
        let m;
        while ((m = answerRegex.exec(answerText)) !== null) {
            const qNum = parseInt(m[1]);
            const letter = m[2].toUpperCase();
            answerMap[qNum] = letter;
            console.log(`Found answer for Q${qNum}: ${letter}`);
            
            // Try to extract explanation (text after the answer until next question or end)
            const afterAnswer = answerText.substring(m.index + m[0].length);
            const nextQ = afterAnswer.search(/Question\s+\d+\s+Answer:/i);
            let expText = nextQ > -1 ? afterAnswer.substring(0, nextQ) : afterAnswer;
            // Strip "Explanation:" prefix (may be preceded by newlines/whitespace)
            expText = expText.replace(/[\s\S]*?Explanation:\s*/i, '').trim();
            if (expText) {
                explanationMap[qNum] = expText.substring(0, 200); // Limit length
            }
        }
        console.log("Answer map:", answerMap);
    }

    // 3. Parse Questions
    let html = '<div class="quiz-container">';
    
    // Insert newlines before question numbers to make splitting easier
    // Handle both "Question 1" and "1." formats
    let normalized = questionText
        .replace(/####+\s*/gi, '\n')  // Remove all ### markers
        .replace(/\*\*(.+?)\*\*/g, '$1')  // Remove **bold** markers from quiz titles
        .replace(/\s+Question\s+(\d+)/gi, '\nQuestion $1') // Force newline before "Question X"
        .replace(/(^|\n)\s*(\d{1,2})\.\s+/g, '\n$2. ');  // Newline before "N. " only at line-start (1-2 digit numbers)

    console.log("Normalized text (first 500 chars):", normalized.substring(0, 500));

    // Split by either "Question X" OR "X." at start of line (without \s requirement)
    const pieces = normalized.split(/\n(?=(?:Question\s+\d+|\d+\.))/i);
    
    console.log("Split into", pieces.length, "pieces");
    
    // First piece is intro/header
    if (pieces[0] && pieces[0].trim()) {
        html += `<div class="quiz-intro">${formatMarkdown(pieces[0])}</div>`;
    }

    let questionCount = 0;
    
    for (let i = 1; i < pieces.length; i++) {
        const piece = pieces[i].trim();
        if (!piece) continue;
        
        console.log(`\n--- Processing piece ${i} ---`);
        console.log("Piece preview:", piece.substring(0, 150));
        
        // Extract question number - handle both "Question X" and "X." formats
        const qNumMatch = piece.match(/^(?:Question\s+(\d+)|(\d+)\.)/i);
        if (!qNumMatch) {
            console.log("No question number found, skipping");
            continue;
        }
        
        const qNum = parseInt(qNumMatch[1] || qNumMatch[2]);
        console.log("Question number:", qNum);
        
        // Remove "Question X" or "X." prefix (plus optional colon) and extract the rest
        let remainder = piece.substring(qNumMatch[0].length).replace(/^[\s:]*/, '');

        console.log("Original remainder (first 150 chars):", remainder.substring(0, 150));

        // Insert newline before each option letter so they can be split cleanly.
        // Lookahead avoids consuming the trailing space needed by the next option.
        remainder = remainder.replace(/\s+(?=[A-D][\.\)])/g, '\n');
        // Normalise "A. " to "A) " so downstream parsing is consistent
        remainder = remainder.replace(/^([A-D])\.\s*/gm, '$1) ');

        console.log("After replacement (first 150 chars):", remainder.substring(0, 150));

        const firstOptionIdx = remainder.search(/\n[A-D]\)/);
        
        let questionTextPart = "";
        let optionsText = "";
        
        if (firstOptionIdx > -1) {
            questionTextPart = remainder.substring(0, firstOptionIdx).trim();
            optionsText = remainder.substring(firstOptionIdx);
            console.log("Question text:", questionTextPart.substring(0, 80));
            console.log("Options text preview:", optionsText.substring(0, 100));
        } else {
            console.log("No options found for this question, skipping");
            continue;
        }
        
        html += `<div class="quiz-item" id="q${qNum}">`;
        html += `<div class="quiz-question">${qNum}. ${questionTextPart}</div>`;
        html += `<div class="quiz-options">`;
        
        // Parse each option
        const optionLines = optionsText.split(/\n(?=[A-D]\))/);
        let foundOptions = 0;
        
        for (const optLine of optionLines) {
            const optMatch = optLine.match(/^([A-D])\)\s*(.+)/);
            if (optMatch) {
                foundOptions++;
                const letter = optMatch[1].toUpperCase();
                const optText = optMatch[2].replace(/\s*-{3,}\s*$/, '').trim(); // strip trailing ---
                const isCorrect = answerMap[qNum] === letter;
                
                console.log(`  Option ${letter}: ${optText.substring(0, 40)}... (correct: ${isCorrect})`);
                
                html += `<div class="quiz-option" onclick="checkAnswer(this, ${isCorrect}, 'q${qNum}-exp')">`;
                html += `<div class="option-marker"><span>${letter}</span></div>`;
                html += `<div class="option-content">${optText}</div>`;
                html += `</div>`;
            }
        }
        
        html += `</div>`; // End quiz-options
        
        if (foundOptions > 0) {
            questionCount++;
            // Add explanation div
            const explanation = explanationMap[qNum] || (answerMap[qNum] ? `The correct answer is ${answerMap[qNum].toUpperCase()}.` : 'No explanation available.');
            html += `<div id="q${qNum}-exp" class="quiz-explanation">
                        <strong>Explanation:</strong> ${explanation}
                     </div>`;
        }
        
        html += `</div>`; // End quiz-item
    }
    
    html += '</div>';
    
    console.log(`=== Finished rendering: ${questionCount} questions ===`);
    
    // If no questions were parsed, throw error to fall back
    if (questionCount === 0) {
        throw new Error("No quiz questions could be parsed");
    }
    
    return html;
}

// Helper to format basic markdown chunks inside the quiz
function formatMarkdown(text) {
  if (!text) return "";
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\n/g, "<br>");
  return text;
}

// Render quiz from structured JSON { type:"quiz", questions:[...] }
function renderQuizFromJSON(data) {
    let html = '<div class="quiz-container">';

    // Normalize: support "questions", "quiz" as the array key
    const questions = data.questions || data.quiz || [];

    questions.forEach((q, idx) => {
        const qNum = idx + 1;
        const letters = ["A", "B", "C", "D"];

        // Normalize options: support "options" or "choices"; if array, convert to {A, B, C, D} object
        let options = q.options || q.choices;
        if (Array.isArray(options)) {
            const obj = {};
            options.forEach((val, i) => { if (i < 4) obj[letters[i]] = val; });
            options = obj;
        }

        // Normalize answer: if numeric index, convert to letter
        let answer = q.answer;
        if (typeof answer === "number") {
            answer = letters[answer] || "";
        }
        if (typeof answer === "string") {
            answer = answer.toUpperCase();
        }

        html += `<div class="quiz-item" id="q${qNum}">`;
        html += `<div class="quiz-question">${qNum}. ${q.question}</div>`;
        html += `<div class="quiz-options">`;

        letters.forEach(letter => {
            if (!options[letter]) return;
            const isCorrect = answer === letter;
            html += `<div class="quiz-option" onclick="checkAnswer(this, ${isCorrect}, 'q${qNum}-exp')">`;
            html += `<div class="option-marker"><span>${letter}</span></div>`;
            html += `<div class="option-content">${options[letter]}</div>`;
            html += `</div>`;
        });

        html += `</div>`; // end quiz-options
        html += `<div id="q${qNum}-exp" class="quiz-explanation">`;
        html += `<strong>Explanation:</strong> ${q.explanation || "No explanation available."}`;
        html += `</div>`;
        html += `</div>`; // end quiz-item
    });

    html += '</div>';
    return html;
}

// Render flashcards from structured JSON { type:"flashcards", cards:[...] }
function renderFlashcardsFromJSON(data) {
    let html = '<div class="flashcards-container">';

    // Normalize: support both "cards" and "flashcards" as the array key
    const cards = data.cards || data.flashcards || [];

    cards.forEach((card, idx) => {
        const cardNum = idx + 1;
        // Normalize: support both front/back and question/answer keys
        const front = card.front || card.question || "";
        const back = card.back || card.answer || "";

        html += `
            <div class="flashcard" onclick="this.classList.toggle('flipped')">
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <div class="flashcard-number">Card ${cardNum}</div>
                        <div class="flashcard-content">${front}</div>
                        <div class="flashcard-hint">Click to reveal answer</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="flashcard-number">Card ${cardNum} - Answer</div>
                        <div class="flashcard-content">${back}</div>
                        <div class="flashcard-hint">Click to flip back</div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

// Render interactive flashcards with flip animation
function renderInteractiveFlashcards(text) {
    console.log("Rendering interactive flashcards...");
    console.log("Original text (first 500 chars):", text.substring(0, 500));

    let html = '<div class="flashcards-container">';

    // Split by --- separators first to get individual cards
    const cardSections = text.split(/---+/).filter(s => s.trim());
    
    console.log(`Split into ${cardSections.length} sections`);
    
    let cardCount = 0;
    
    for (const section of cardSections) {
        // Look for "Card N" pattern to get card number
        const cardNumMatch = section.match(/Card\s+(\d+)/i);
        if (!cardNumMatch) continue;
        
        const cardNum = cardNumMatch[1];
        
        // Extract Front and Back content
        // Handle format: "Card N Front: ... Back: ..."
        const frontBackMatch = section.match(/Front:\s*(.+?)\s*Back:\s*(.+)/is);
        
        if (!frontBackMatch) {
            console.log(`Card ${cardNum} - couldn't find Front/Back pattern`);
            continue;
        }
        
        let front = frontBackMatch[1].trim();
        let back = frontBackMatch[2].trim();
        
        // Clean up any remaining markers or extra whitespace
        front = front.replace(/---+/g, '').replace(/\s+/g, ' ').trim();
        back = back.replace(/---+/g, '').replace(/\s+/g, ' ').trim();
        
        console.log(`Card ${cardNum} - Front: ${front.substring(0, 50)}...`);
        console.log(`Card ${cardNum} - Back: ${back.substring(0, 50)}...`);
        
        cardCount++;

        html += `
            <div class="flashcard" onclick="this.classList.toggle('flipped')">
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <div class="flashcard-number">Card ${cardNum}</div>
                        <div class="flashcard-content">${front}</div>
                        <div class="flashcard-hint">Click to reveal answer</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="flashcard-number">Card ${cardNum} - Answer</div>
                        <div class="flashcard-content">${back}</div>
                        <div class="flashcard-hint">Click to flip back</div>
                    </div>
                </div>
            </div>
        `;
    }

    html += '</div>';
    
    console.log(`Flashcards HTML generated successfully: ${cardCount} cards`);
    
    if (cardCount === 0) {
        console.error("No flashcards could be parsed");
        return `<div style="padding: 20px; color: red;">Failed to parse flashcards. Raw text: ${text.substring(0, 500)}</div>`;
    }
    
    return html;
}

// Global function to check answers
window.checkAnswer = function (element, isCorrect, explanationId) {
  // Prevent multiple clicks if already answered
  const parent = element.parentElement;
  if (
    parent.querySelector(".quiz-option.correct") ||
    parent.querySelector(".quiz-option.incorrect")
  ) {
    return;
  }

  if (isCorrect) {
    element.classList.add("correct");
  } else {
    element.classList.add("incorrect");

    // Highlight the correct answer
    const allOptions = parent.querySelectorAll(".quiz-option");
    allOptions.forEach(option => {
      // Find the correct answer by checking the onclick attribute
      const onclickAttr = option.getAttribute("onclick");
      if (onclickAttr && onclickAttr.includes("true")) {
        option.classList.add("correct");
      }
    });
  }

  // Show explanation
  const expDiv = document.getElementById(explanationId);
  if (expDiv) {
    expDiv.style.display = "block";
  }
};

// Quick action buttons
function quickAction(action) {
  const input = document.getElementById("user-input");
  const quizCount = document.getElementById("quiz-count").value;
  const difficulty = document.getElementById("difficulty").value;
  const flashcardCount = document.getElementById("flashcard-count").value;

  let prompt = "";

  switch (action) {
    case "summarize":
      prompt = "Summarize the topic: ";
      break;
    case "quiz":
      prompt = `Create a ${quizCount}-question quiz on "[topic]" at ${difficulty} level`;
      break;
    case "explain":
      prompt = `Explain the concept "[concept]" at ${difficulty} level`;
      break;
    case "flashcards":
      prompt = `Create ${flashcardCount} flashcards for: `;
      break;
    case "compare":
      prompt = "Compare these concepts: ";
      break;
  }

  input.value = prompt;
  input.focus();

  // Select placeholder text
  if (prompt.includes("[")) {
    const start = prompt.indexOf("[");
    const end = prompt.indexOf("]") + 1;
    input.setSelectionRange(start, end);
  }
}

// Toggle answers visibility
function toggleAnswers(button) {
  const answersContent = button.nextElementSibling;
  if (answersContent && answersContent.classList.contains("answers-content")) {
    if (answersContent.style.display === "block") {
      answersContent.style.display = "none";
      button.textContent = "Show Answers";
    } else {
      answersContent.style.display = "block";
      button.textContent = "Hide Answers";
    }
  }
}
