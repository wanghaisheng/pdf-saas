import * as vueComponents from './components';
import '@laws-africa/web-components/dist/components/la-akoma-ntoso';
import '@laws-africa/web-components/dist/components/la-gutter';
import '@laws-africa/web-components/dist/components/la-gutter-item';
import './compat-imports';
import { createComponent, getVue, registerComponents } from './vue';

class IndigoApp {
  setup () {
    this.components = [];
    this.Vue = getVue();

    registerComponents(vueComponents);
    window.dispatchEvent(new Event('indigo.vue-components-registered'));

    this.createVueComponents(document);
    window.dispatchEvent(new Event('indigo.components-created'));
  }

  /**
   * Create Vue-based components on this root and its descendants.
   * @param root
   */
  createVueComponents (root) {
    // create vue-based components
    for (const element of root.querySelectorAll('[data-vue-component]')) {
      this.createVueComponent(element);
    }
  }

  createVueComponent (element) {
    const name = element.getAttribute('data-vue-component');

    if (this.Vue.options.components[name]) {
      // create the component and attached it to the HTML element
      const vue = createComponent(name, { el: element });
      vue.$el.component = vue;
      this.components.push(vue);
    }
  }
}

export default new IndigoApp();
