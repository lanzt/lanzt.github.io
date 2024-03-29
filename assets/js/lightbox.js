const lightbox = document.createElement("div");
lightbox.id = "lightbox";
document.body.appendChild(lightbox);

const images = document.querySelectorAll(".article-post img");

images.forEach((image) => {
  image.addEventListener("click", (e) => {
    lightbox.classList.add("active");
    const img = document.createElement("img");
    img.src = image.src;
    while (lightbox.firstChild) {
      lightbox.removeChild(lightbox.firstChild);
    }
    img.style.setProperty("cursor", "vertical-text");
    lightbox.appendChild(img);
    lightbox.style.setProperty("cursor", "pointer");
  });
});

lightbox.addEventListener("click", (e) => {
  if (e.target !== e.currentTarget) return;
  lightbox.classList.remove("active");
});

// Agregamos la lógica para cerrar la imagen al hacer scroll
document.addEventListener("scroll", () => {
  if (lightbox.classList.contains("active")) {
    closeLightbox();
  }
});

function closeLightbox() {
  lightbox.classList.remove("active");
}