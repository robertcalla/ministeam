// remove as mensagens de erro ou sucesso apos 4 segundos para a tela nao ficar poluida
document.addEventListener("DOMContentLoaded", function() {
    const flashes = document.querySelectorAll('.flash');
    if (flashes.length > 0) {
        setTimeout(() => {
            flashes.forEach(flash => {
                flash.style.opacity = '0';
                setTimeout(() => flash.remove(), 500);
            });
        }, 4000);
    }
});