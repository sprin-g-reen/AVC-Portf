document.addEventListener("DOMContentLoaded", () => {
  // Preloader
  const preloader = document.getElementById('preloader');
  if (preloader) preloader.style.display = 'none';
  document.body.style.position = 'static';

  // In forced desktop-mode on mobile, prevent carried horizontal offset across pages.
  if (window.innerWidth < 992) {
    const bodyMinWidth = parseFloat(window.getComputedStyle(document.body).minWidth || "0");
    if (bodyMinWidth >= 1200) {
      window.scrollTo(0, 0);
    }
  }

  // HEADER NAV IN MOBILE
  const sidebar = document.querySelector(".ul-sidebar");
  const opener = document.querySelector(".ul-header-sidebar-opener");
  const closer = document.querySelector(".ul-sidebar-closer");
  const mobileMenuContent = document.querySelector(".to-go-to-sidebar-in-mobile");
  const headerNavMobileWrapper = document.querySelector(".ul-sidebar-header-nav-wrapper");
  const headerNavOgWrapper = document.querySelector(".ul-header-nav-wrapper");
  const inlineMobileNavToggle = document.querySelector(".ul-mobile-nav-toggle");
  const headerNavMobile = document.querySelector(".ul-header-nav");
  const useSidebarMenu = Boolean(opener && sidebar && headerNavMobileWrapper && headerNavOgWrapper && !inlineMobileNavToggle);

  function updateMenuPosition() {
    if (!mobileMenuContent || !headerNavOgWrapper) return;
    if (!useSidebarMenu) {
      if (!headerNavOgWrapper.contains(mobileMenuContent)) {
        headerNavOgWrapper.appendChild(mobileMenuContent);
      }
      return;
    }

    if (window.innerWidth < 992) {
      if (!headerNavMobileWrapper.contains(mobileMenuContent)) {
        headerNavMobileWrapper.appendChild(mobileMenuContent);
      }
    } else {
      if (!headerNavOgWrapper.contains(mobileMenuContent)) {
        headerNavOgWrapper.appendChild(mobileMenuContent);
      }
    }
  }
  updateMenuPosition();
  window.addEventListener("resize", updateMenuPosition);

  if (opener && sidebar) opener.addEventListener("click", () => sidebar.classList.add("active"));
  if (closer && sidebar) closer.addEventListener("click", () => sidebar.classList.remove("active"));

  // Inline mobile nav fallback for pages without sidebar markup
  if (inlineMobileNavToggle && headerNavMobile) {
    const syncInlineMobileNav = () => {
      if (window.innerWidth >= 992) {
        headerNavMobile.classList.remove("is-open");
        inlineMobileNavToggle.setAttribute("aria-expanded", "false");
      }
    };

    inlineMobileNavToggle.addEventListener("click", () => {
      const isOpen = headerNavMobile.classList.toggle("is-open");
      inlineMobileNavToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    syncInlineMobileNav();
    window.addEventListener("resize", syncInlineMobileNav);
  }

  // Menu dropdown/submenu in mobile
  if (headerNavMobile) {
    let activeMegaPortal = null;

    const clearMegaMenuInlineStyles = (submenu) => {
      if (!submenu) return;
      submenu.style.removeProperty("display");
      submenu.style.removeProperty("position");
      submenu.style.removeProperty("left");
      submenu.style.removeProperty("top");
      submenu.style.removeProperty("width");
      submenu.style.removeProperty("max-height");
      submenu.style.removeProperty("z-index");
      submenu.style.removeProperty("opacity");
      submenu.style.removeProperty("visibility");
      submenu.style.removeProperty("pointer-events");
      submenu.style.removeProperty("transform");
    };

    const closeActiveMegaMenus = () => {
      if (activeMegaPortal) {
        const { item, submenu, placeholder } = activeMegaPortal;
        if (placeholder?.parentNode) {
          placeholder.parentNode.insertBefore(submenu, placeholder);
          placeholder.parentNode.removeChild(placeholder);
        }
        item.classList.remove("active");
        clearMegaMenuInlineStyles(submenu);
        activeMegaPortal = null;
        return;
      }

      const openMegaMenus = headerNavMobile.querySelectorAll(".has-mega-menu.active");
      openMegaMenus.forEach((menu) => menu.classList.remove("active"));
    };

    const openMegaMenuAsOverlay = (item, submenu) => {
      if (!item || !submenu) return;
      const trigger = item.querySelector(":scope > a");
      if (!trigger) return;

      closeActiveMegaMenus();

      const parent = submenu.parentNode;
      if (!parent) return;
      const placeholder = document.createComment("mega-menu-placeholder");
      parent.insertBefore(placeholder, submenu);
      document.body.appendChild(submenu);

      const rect = trigger.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const desiredWidth = Math.min(170, viewportWidth - 16);
      let left = rect.left;
      if (left + desiredWidth > viewportWidth - 8) left = viewportWidth - desiredWidth - 8;
      if (left < 8) left = 8;
      const top = rect.bottom + 6;
      const maxHeight = Math.max(160, window.innerHeight - top - 12);

      submenu.style.display = "block";
      submenu.style.position = "fixed";
      submenu.style.left = `${Math.round(left)}px`;
      submenu.style.top = `${Math.round(top)}px`;
      submenu.style.width = `${Math.round(desiredWidth)}px`;
      submenu.style.maxHeight = `${Math.round(maxHeight)}px`;
      submenu.style.zIndex = "2147483647";
      submenu.style.opacity = "1";
      submenu.style.visibility = "visible";
      submenu.style.pointerEvents = "all";
      submenu.style.transform = "none";

      item.classList.add("active");
      activeMegaPortal = { item, submenu, placeholder };
    };

    const items = headerNavMobile.querySelectorAll(".has-sub-menu");
    items.forEach((item) => {
      const trigger = item.querySelector(":scope > a");
      const submenu = item.querySelector(":scope > .ul-header-submenu");
      if (!trigger) return;

      trigger.addEventListener("click", (e) => {
        if (window.innerWidth < 992) {
          e.preventDefault();
          const isMegaMenu = item.classList.contains("has-mega-menu") && submenu;
          const isAlreadyActive = item.classList.contains("active");

          if (isMegaMenu) {
            if (isAlreadyActive) closeActiveMegaMenus();
            else openMegaMenuAsOverlay(item, submenu);
          } else {
            item.classList.toggle("active");
          }
        }
      });
    });

    // Close overlay dropdown on scroll/resize so it doesn't stay floating while page moves.
    window.addEventListener("scroll", () => {
      if (window.innerWidth < 992) closeActiveMegaMenus();
    }, { passive: true });

    window.addEventListener("resize", () => {
      if (window.innerWidth >= 992) closeActiveMegaMenus();
    });

    document.addEventListener("click", (event) => {
      if (window.innerWidth >= 992) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (activeMegaPortal && activeMegaPortal.submenu.contains(target)) return;
      if (!headerNavMobile.contains(target)) closeActiveMegaMenus();
    });
  }

  // Header search in mobile
  const searchOpener = document.querySelector(".ul-header-mobile-search-opener");
  const searchCloser = document.querySelector(".ul-header-mobile-search-closer");
  const searchFormWrapper = document.querySelector(".ul-header-search-form-wrapper");
  if (searchOpener && searchFormWrapper) searchOpener.addEventListener("click", () => searchFormWrapper.classList.add("active"));
  if (searchCloser && searchFormWrapper) searchCloser.addEventListener("click", () => searchFormWrapper.classList.remove("active"));

  // Header top Splide slider
  if (document.querySelector(".ul-header-top-slider") && typeof Splide !== 'undefined') {
    try {
      new Splide('.ul-header-top-slider', {
        arrows: false,
        pagination: false,
        type: 'loop',
        drag: 'free',
        focus: 0,
        perPage: 9,
        autoWidth: true,
        trimSpace: false,
        gap: 15,
        autoScroll: { speed: 1.5 },
      }).mount(window.splide?.Extensions || {});
    } catch (e) { /* no-op */ }
  }

  // SlimSelect for search category (support both legacy and new IDs)
  let searchSelectSelector = null;
  if (document.getElementById('ul-header-search-category')) {
    searchSelectSelector = '#ul-header-search-category';
  } else if (document.getElementById('headerSearchCategory')) {
    searchSelectSelector = '#headerSearchCategory';
  }
  if (searchSelectSelector && typeof SlimSelect !== 'undefined') {
    new SlimSelect({
      select: searchSelectSelector,
      settings: { showSearch: false }
    });
  }

  // MixItUp filtering
  if (document.querySelector(".ul-filter-products-wrapper") && typeof mixitup !== 'undefined') {
    mixitup('.ul-filter-products-wrapper');
  }

  // Swiper sliders
  if (typeof Swiper !== 'undefined') {
    // Banner thumbs slider
    let bannerThumbSlider = null;
    if (document.querySelector(".ul-banner-img-slider")) {
      bannerThumbSlider = new Swiper(".ul-banner-img-slider", {
        slidesPerView: 1.4,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 15,
        breakpoints: {
          992: { spaceBetween: 15 },
          1680: { spaceBetween: 26 },
          1700: { spaceBetween: 30 },
        },
      });
    }

    // Main banner slider
    if (document.querySelector(".ul-banner-slider")) {
      new Swiper(".ul-banner-slider", {
        slidesPerView: 1,
        loop: true,
        autoplay: { delay: 3000 },
        thumbs: bannerThumbSlider ? { swiper: bannerThumbSlider } : undefined,
        navigation: {
          nextEl: ".ul-banner-slider-nav .next",
          prevEl: ".ul-banner-slider-nav .prev",
        },
      });
    }

    // Product sliders
    if (document.querySelector(".ul-products-slider-1")) {
      new Swiper(".ul-products-slider-1", {
        slidesPerView: 3,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 15,
        navigation: { nextEl: ".ul-products-slider-1-nav .next", prevEl: ".ul-products-slider-1-nav .prev" },
        breakpoints: {
          0: { slidesPerView: 1 },
          480: { slidesPerView: 2 },
          992: { slidesPerView: 3 },
          1200: { spaceBetween: 20 },
          1400: { spaceBetween: 22 },
          1600: { spaceBetween: 26 },
          1700: { spaceBetween: 30 },
        },
      });
    }

    if (document.querySelector(".ul-products-slider-2")) {
      new Swiper(".ul-products-slider-2", {
        slidesPerView: 3,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 15,
        navigation: { nextEl: ".ul-products-slider-2-nav .next", prevEl: ".ul-products-slider-2-nav .prev" },
        breakpoints: {
          0: { slidesPerView: 1 },
          480: { slidesPerView: 2 },
          992: { slidesPerView: 3 },
          1200: { spaceBetween: 20 },
          1400: { spaceBetween: 22 },
          1600: { spaceBetween: 26 },
          1700: { spaceBetween: 30 },
        },
      });
    }

    if (document.querySelector(".ul-flash-sale-slider")) {
      new Swiper(".ul-flash-sale-slider", {
        slidesPerView: 1,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 15,
        breakpoints: {
          480: { slidesPerView: 2 },
          768: { slidesPerView: 3 },
          992: { slidesPerView: 4 },
          1200: { spaceBetween: 20, slidesPerView: 4 },
          1680: { spaceBetween: 26, slidesPerView: 4 },
          1700: { spaceBetween: 30, slidesPerView: 4.7 },
        },
      });
    }

    if (document.querySelector(".ul-reviews-slider")) {
      new Swiper(".ul-reviews-slider", {
        slidesPerView: 1,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 15,
        breakpoints: {
          768: { slidesPerView: 2 },
          992: { spaceBetween: 20, slidesPerView: 3 },
          1200: { spaceBetween: 20, slidesPerView: 4 },
          1680: { slidesPerView: 4, spaceBetween: 26 },
          1700: { slidesPerView: 4, spaceBetween: 30 },
        },
      });
    }

    if (document.querySelector(".ul-gallery-slider")) {
      new Swiper(".ul-gallery-slider", {
        slidesPerView: 2.2,
        loop: true,
        autoplay: { delay: 3000 },
        centeredSlides: true,
        spaceBetween: 15,
        breakpoints: {
          480: { slidesPerView: 3.4 },
          576: { slidesPerView: 4 },
          768: { slidesPerView: 5 },
          992: { spaceBetween: 20, slidesPerView: 5.5 },
          1680: { spaceBetween: 26, slidesPerView: 5.5 },
          1700: { spaceBetween: 30, slidesPerView: 5.5 },
          1920: { spaceBetween: 30, slidesPerView: 6, centeredSlides: false },
        },
      });
    }

    if (document.querySelector(".ul-sidebar-products-slider")) {
      new Swiper(".ul-sidebar-products-slider", {
        slidesPerView: 1,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 30,
        navigation: { nextEl: ".ul-sidebar-products-slider-nav .next", prevEl: ".ul-sidebar-products-slider-nav .prev" },
        breakpoints: { 1400: { slidesPerView: 2 } },
      });
    }

    if (document.querySelector(".ul-product-details-img-slider")) {
      window.ulProductDetailsSwiper = new Swiper(".ul-product-details-img-slider", {
        slidesPerView: 1,
        loop: true,
        autoplay: { delay: 3000 },
        spaceBetween: 0,
        navigation: { nextEl: "#ul-product-details-img-slider-nav .next", prevEl: "#ul-product-details-img-slider-nav .prev" },
      });
    }
  }

  // Product page price filter (noUiSlider)
  const priceFilterSlider = document.getElementById('ul-products-price-filter-slider');
  if (priceFilterSlider && typeof noUiSlider !== 'undefined') {
    noUiSlider.create(priceFilterSlider, {
      start: [20, 80],
      connect: true,
      range: { 'min': 0, 'max': 100 }
    });
  }

  // Quantity field
  if (document.querySelector(".ul-product-quantity-wrapper")) {
    const quantityWrappers = document.querySelectorAll(".ul-product-quantity-wrapper");
    quantityWrappers.forEach((item) => {
      const quantityInput = item.querySelector(".ul-product-quantity");
      const incBtn = item.querySelector(".quantityIncreaseButton");
      const decBtn = item.querySelector(".quantityDecreaseButton");
      if (incBtn && quantityInput) incBtn.addEventListener("click", () => quantityInput.value = parseInt(quantityInput.value || '0') + 1);
      if (decBtn && quantityInput) decBtn.addEventListener("click", () => {
        const current = parseInt(quantityInput.value || '1');
        if (current > 1) quantityInput.value = current - 1;
      });
    });
  }

  // Parallax effect
  const parallaxImage = document.querySelector(".ul-video-cover");
  if (parallaxImage) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          window.addEventListener("scroll", parallaxEffect);
          parallaxEffect();
        } else {
          window.removeEventListener("scroll", parallaxEffect);
        }
      });
    });
    observer.observe(parallaxImage);

    function parallaxEffect() {
      const rect = parallaxImage.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      const imageCenter = rect.top + rect.height / 2;
      const viewportCenter = windowHeight / 2;
      const offset = (imageCenter - viewportCenter) * -0.5;
      parallaxImage.style.transform = `translateY(${offset}px)`;
    }
  }
});
