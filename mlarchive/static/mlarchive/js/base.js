/* base.js */

var base = {

    // VARAIBLES =============================================
    isLegacyOn: $.cookie('isLegacyOn') == "true" ? true : false,

    // PRIMARY FUNCTIONS =====================================
    
    init: function() {
        base.cacheDom();
        base.bindEvents();
        base.initLegacy();
    },

    cacheDom: function() {
        base.$toggleLegacyLink = $('#toggle-legacy');
    },

    bindEvents: function() {
        base.$toggleLegacyLink.on('click', base.toggleLegacy);
    },

    initLegacy: function() {
        if(base.isLegacyOn) {
            base.$toggleLegacyLink.text("Legacy Mode Off");
        }
    },

    toggleLegacy: function() {
        event.preventDefault();
        if(base.isLegacyOn) {
            base.isLegacyOn = false;
            $.cookie('isLegacyOn','false', { expires: 5*365, path: '/'});
            base.$toggleLegacyLink.text("Legacy Mode On");
            if(typeof mailarch !== 'undefined'){
                mailarch.legacyOff();
            }
        } else {
            base.isLegacyOn = true;
            $.cookie('isLegacyOn','true', { expires: 5*365, path: '/'});
            base.$toggleLegacyLink.text("Legacy Mode Off");
            if(typeof mailarch !== 'undefined'){
                mailarch.legacyOn();
            }
        }
    },
}

$(function() {
    base.init();
});