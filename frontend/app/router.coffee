`import Ember from 'ember'`

Router = Ember.Router.extend(
  location: AmazonRepricerENV.locationType
)

Router.map(() ->
    @route('inquiry')
    @route('listings')
    @route('sellers')
    @route('results')
)

`export default Router`
