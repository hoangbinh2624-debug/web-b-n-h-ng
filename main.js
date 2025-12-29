$(function () {
  // Smooth scroll đến các section
  $("#right-menu a, .navbar-nav .nav-link[href^='#']").on(
    "click",
    function (e) {
      var target = $($(this).attr("href"));
      if (target.length) {
        e.preventDefault();
        $("html, body").animate({ scrollTop: target.offset().top - 70 }, 500);
      }
    }
  );

  // Banner slider tự động chuyển động
  let $slides = $(".header-slider .slide-img");
  let idx = 0;
  function showSlide(i) {
    $slides.removeClass("active");
    $slides.eq(i).addClass("active");
  }
  if ($slides.length) {
    showSlide(0);
    setInterval(function () {
      idx = (idx + 1) % $slides.length;
      showSlide(idx);
    }, 2000);
  }
});
