`import Ember from "ember"`

IndexRoute = Ember.Route.extend({
    beforeModel: () ->
        @transitionTo("inquiry")
});

`export default IndexRoute`