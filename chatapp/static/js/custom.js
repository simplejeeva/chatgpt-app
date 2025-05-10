function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie("csrftoken");

let form = document.querySelector(".submit-form");
let input = document.querySelector("#input_value");

let heading = document.querySelector("#main-header");
let bot_container = document.querySelector(".bot-feature-container");
let container = document.querySelector(".container-fluid-2");
let spinner = document.querySelector(".spinner-main");

form.addEventListener("submit", submitForm);
let selectedModel = "openai"; // Default model is OpenAI

// Handle model change
document.querySelectorAll(".model-btn").forEach((item) => {
  item.addEventListener("click", (event) => {
    selectedModel = event.target.dataset.model;
    console.log("Selected Model:", selectedModel); // Log for debugging
  });
});

async function postJSON(data) {
  spinner.style.display = "flex";
  const url = "/get-value/"; // ✅ trailing slash added
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
      body: JSON.stringify({
        msg: data.msg,
        model: selectedModel, // Pass the selected model to the server
      }),
    });

    const result = await response.json();
    heading.style.display = "none";
    bot_container.style.display = "none";
    spinner.style.display = "none";

    container.innerHTML += `
      <div class="chat-container">
          <div class="user-chat-container">
              <div class="user-pic"><i class="fa-solid fa-circle-user"></i></div>
              <div class="user-message">${result.msg}</div>
          </div>
         
 <div class="bot-chat-container">
                <div class="bot-icon"><i class="fa-solid fa-robot"></i></div>
              <div class="bot-response">${result.res} </div>
          </div>
          <div class="ai-source">
              <strong>Source: </strong> ${result.model} <!-- Display the model source -->
          </div>
          </div>
      </div>`;

    input.value = "";
    console.log("Success:", result);
  } catch (error) {
    spinner.style.display = "none";
    console.error("Error:", error);
  }
}
function submitForm(e) {
  e.preventDefault();
  let message = input.value;
  const data = { msg: message };
  document.querySelector("#submit-btn").disabled = true;
  postJSON(data);
}

// ===================================
function adjustFontSize() {
  const botResponses = document.querySelectorAll(".bot-response");
  if (window.innerWidth <= 768) {
    botResponses.forEach((element) => {
      element.style.fontSize = "0.8em"; // Adjust font size for smaller screens
    });
  } else {
    botResponses.forEach((element) => {
      element.style.fontSize = "1em"; // Default font size for larger screens
    });
  }
}

// Run the function initially and whenever the window is resized
window.addEventListener("resize", adjustFontSize);
adjustFontSize();

// ==============================?
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("pdf-upload-form");

  form.addEventListener("submit", async function (e) {
    e.preventDefault(); // Stop normal form submit

    const formData = new FormData(form);

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
        },
      });

      if (response.ok) {
        alert("PDF uploaded successfully!");
        const modalElement = document.getElementById("pdfUploadModal");
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        modalInstance.hide(); // ✅ Hides the modal on success

        form.reset(); // Optional: clear the form
      } else {
        alert("Upload failed. Please try again.");
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("An error occurred. Please try again.");
    }
  });
});
