$(document).ready(function () {
  var loading = false;

  $(window).scroll(function () {
    if ($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
      if (!loading) {
        loading = true;
        // Fetch more winning meals using AJAX
        $.ajax({
          url: "/fetch_more_meals", // Replace with your API route for fetching more meals
          type: "GET",
          success: function (data) {
            // Append the new meals to the meal container
            $("#meal-container").append(data);

            // Allow loading more meals again
            loading = false;
          },
        });
      }
    }
  });
});
