(function(exports) {
  "use strict";

  if (!exports.Indigo) exports.Indigo = {};
  Indigo = exports.Indigo;

  // django doesn't link blank date fields, send null instead
  function emptyIsNull(val) {
    return (!val || val.trim() === "") ? null : val;
  }

  /**
   * A view that lets a user create or edit a Work.
   */
  Indigo.WorkView = Backbone.View.extend({
    el: '#edit-work-view',
    events: {
      'click .btn.save': 'save',
      'click .btn.delete': 'deleteWork',
      'click .change-repeal': 'changeRepeal',
      'click .delete-repeal': 'deleteRepeal',
      'click .choose-parent': 'changeParent',
      'click .delete-parent': 'deleteParent',
      'click .change-commencing-work': 'changeCommencingWork',
      'click .delete-commencing-work': 'deleteCommencingWork',
    },
    workRepealTemplate: '#work-repeal-template',
    commencingWorkTemplate: '#commencing-work-template',
    bindings: {
      '#work_country': {
        observe: 'country',
        onSet: function(val) {
          // trigger a redraw of the localities, using this country
          this.country = val;
          this.model.set('locality', null);
          this.model.trigger('change:locality', this.model);
          return val;
        },
      },
      '#work_locality': {
        observe: 'locality',
        selectOptions: {
          collection: function() {
            var country = Indigo.countries[this.country || this.model.get('country')];
            return country ? country.localities : [];
          },
          defaultOption: {label: "(none)", value: null},
        }
      },
      '#work_nature': 'nature',
      '#work_subtype': 'subtype',
      '#work_year': 'year',
      '#work_number': 'number',
      '#work_frbr_uri': 'frbr_uri',
      '#work_title': 'title',
      '#work_publication_date': {
        observe: 'publication_date',
        onSet: emptyIsNull,
      },
      '#work_publication_name': 'publication_name',
      '#work_publication_number': 'publication_number',
      '#work_commencement_date': {
        observe: 'commencement_date',
        onSet: emptyIsNull,
      },
      '#work_assent_date': {
        observe: 'assent_date',
        onSet: emptyIsNull,
      },
      '#work_repealed_date': {
        observe: 'repealed_date',
        onSet: emptyIsNull,
      },
    },

    initialize: function(options) {
      this.dirty = false;

      this.workRepealTemplate = Handlebars.compile($(this.workRepealTemplate).html());
      this.commencingWorkTemplate = Handlebars.compile($(this.commencingWorkTemplate).html());

      this.model = new Indigo.Work(Indigo.Preloads.work, {parse: true});
      this.listenTo(this.model, 'change:country', this.updatePublicationOptions);
      this.listenTo(this.model, 'change:country change:locality', this.updateBreadcrumb);
      this.listenTo(this.model, 'change:title change:frbr_uri', this.updatePageTitle);
      this.listenTo(this.model, 'change', this.setDirty);

      this.listenTo(this.model, 'sync', this.setClean);
      this.listenTo(this.model, 'change', this.canSave);
      this.listenTo(this.model, 'change:repealed_by', this.repealChanged);
      this.listenTo(this.model, 'change:commencing_work', this.commencingWorkChanged);
      this.listenTo(this.model, 'change:parent_work', this.parentChanged);

      // prevent the user from navigating away without saving changes
      $(window).on('beforeunload', _.bind(this.windowUnloading, this));

      this.model.updateFrbrUri();
      this.listenToOnce(Indigo.works, 'sync', this.parentChanged);
      this.updatePublicationOptions();
      this.stickit();
      this.repealChanged();
      this.commencingWorkChanged();
      this.canSave();
    },

    updatePageTitle: function() {
      document.title = this.model.get('title') + ' - Indigo';
      if (!this.model.isNew()) $('.workspace-header h4, .work-title').text(this.model.get('title'));
      this.$('.work-frbr-uri').text(this.model.get('frbr_uri'));
    },

    setDirty: function() {
      this.dirty = true;
      this.canSave();
    },

    setClean: function() {
      this.dirty = false;
      this.canSave();
    },

    updatePublicationOptions: function() {
      var country = Indigo.countries[this.model.get('country')],
          pubs = (country ? country.publications : []).sort();

      $("#publication_list").empty().append(_.map(pubs, function(pub) {
        var opt = document.createElement("option");
        opt.setAttribute("value", pub);
        return opt;
      }));
    },

    updateBreadcrumb: function() {
      var country = Indigo.countries[this.model.get('country')],
          locality = this.model.get('locality');

      this.$('.work-country')
        .attr('href', '/library?country=' + this.model.get('country'))
        .text(country.name + ' · ' + this.model.get('country'));

      this.$('.work-locality')
        .attr('href', '/library?country=' + this.model.get('country') + '&locality=' + locality)
        .text(locality ? country.localities[locality] + ' · ' + locality : '');
    },

    canSave: function() {
      this.$('.btn.save').attr('disabled', !this.dirty || !this.model.isValid());
    },

    save: function() {
      var self = this,
          isNew = this.model.isNew();

      this.model.save().done(function() {
        if (isNew) {
          // redirect
          Indigo.progressView.peg();
          window.location = '/works/' + self.model.get('id');
        }
      });
    },

    deleteWork: function() {
      if (confirm("Are you sure you want to delete this work?")) {
        this.model.destroy().done(function() {
          window.location = '/';
        });
      }
    },

    deleteRepeal: function(e) {
      e.preventDefault();
      this.model.set('repealed_by', null);
    },

    changeRepeal: function() {
      var chooser = new Indigo.WorkChooserView({}),
          self = this;

      if (this.model.get('repealed_by')) {
        chooser.choose(Indigo.works.get(this.model.get('repealed_by')));
      }
      chooser.setFilters({country: this.model.get('country')});
      chooser.showModal().done(function(chosen) {
        if (chosen) {
          self.model.set('repealed_by', chosen);
          self.model.set('repealed_date', chosen.get('publication_date'));
        }
      });
    },

    repealChanged: function() {
      var repeal,
          repealed_by = this.model.get('repealed_by');

      if (repealed_by) {
        this.$el.addClass('is-repealed');
        this.$('.work-repeal-view').html(this.workRepealTemplate({
          repealed_by: repealed_by.toJSON(),
        }));
      } else {
        this.$el.removeClass('is-repealed');
        this.$('.work-repeal-view').html(this.workRepealTemplate({}));
      }
    },

    deleteCommencingWork: function(e) {
      e.preventDefault();
      this.model.set('commencing_work', null);
    },

    changeCommencingWork: function() {
      var chooser = new Indigo.WorkChooserView({}),
          self = this;

      if (this.model.get('commencing_work')) {
        chooser.choose(Indigo.works.get(this.model.get('commencing_work')));
      }
      chooser.setFilters({country: this.model.get('country')});
      chooser.showModal().done(function(chosen) {
        if (chosen) {
          self.model.set('commencing_work', chosen);
        }
      });
    },

    commencingWorkChanged: function() {
      var commencing_work = this.model.get('commencing_work');

      if (commencing_work) {
        this.$('.work-commencing-work').html(this.commencingWorkTemplate({
          commencing_work: commencing_work.toJSON(),
        }));
      } else {
        this.$('.work-commencing-work').html(this.commencingWorkTemplate({}));
      }
    },

    changeParent: function() {
      var chooser = new Indigo.WorkChooserView({}),
          self = this;

      if (this.model.get('parent_work')) {
        chooser.choose(Indigo.works.get(this.model.get('parent_work')));
      }
      chooser.setFilters({country: this.model.get('country')});
      chooser.showModal().done(function(chosen) {
        if (chosen) {
          self.model.set('parent_work', chosen.get('id'));
        }
      });
    },

    deleteParent: function(e) {
      e.preventDefault();
      this.model.set('parent_work', null);
    },

    parentChanged: function() {
      if (this.model.get('parent_work')) {
        var parent = Indigo.works.get(this.model.get('parent_work'));
        if (!parent) {
          return;
        }

        this.$('#work_parent_work')
          .removeClass('hidden')
          .find('.work_parent_title')
            .text(parent.get('title'))
            .attr('href', '/works/' + parent.get('id'))
            .end()
          .find('.work_parent_uri')
            .text(parent.get('frbr_uri'));
      } else {
        this.$('#work_parent_work').addClass('hidden');
      }
    },

    windowUnloading: function(e) {
      if (this.dirty) {
        e.preventDefault();
        return 'You will lose your changes!';
      }
    },
  });
})(window);
